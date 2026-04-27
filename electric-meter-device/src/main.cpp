#include <Arduino.h>
#include <cstring>

#include "config.h"
#include "secrets.h"

#include "clock.h"
#include "stats.h"

#include "led.h"
#include "pzem004t.h"

#include "ble.h"

#include "flash_memory.h"
#include "mqtt.h"
#include "server.h"
#include "wifi_.h"

board::Clock *sysClock;
board::Stats *stats;

peripherals::Led *builtinLed;
peripherals::Pzem004t *pzem;

server::WifiService *wifi;
server::MqttService *mqtt;
server::ServerStatus serverStatus;

ble::BleService *bleService;

TaskHandle_t syncTimeTaskHandle;
TaskHandle_t serverTaskHandle;

TaskHandle_t deviceStatsTaskHandle;
TaskHandle_t controlTaskHandle;
TaskHandle_t energySamplingTaskHandle;

QueueHandle_t MqttPublishingEventQueue;
QueueHandle_t MqttSubscriptionsEventQueue;

void syncTimeTask(void *pvParameters) {
  for (;;) {
    if (serverStatus == server::ServerStatus::SERVER_STATUS_AVAILABLE) {
      sysClock->syncTime();
      vTaskDelay(pdMS_TO_TICKS(SYNC_TIME_TASK_DELAY_MS));

    } else {
      vTaskDelay(pdMS_TO_TICKS(SYNC_TIME_TASK_RETRY_DELAY_MS));
    }
  }
}

void serverTask(void *pvParameters) {
  for (;;) {
    switch (serverStatus) {
    case server::ServerStatus::SERVER_STATUS_CONNECT_TO_WIFI:
      if (!wifi->credentialsStored())
        break;

      if (wifi->connect())
        serverStatus = server::ServerStatus::SERVER_STATUS_CONNECT_TO_MQTT;

      break;

    case server::ServerStatus::SERVER_STATUS_CONNECT_TO_MQTT:
      if (!wifi->connected()) {
        Serial.println("[Server] WiFi lost, reconnecting");
        serverStatus = server::ServerStatus::SERVER_STATUS_CONNECT_TO_WIFI;

      } else if (!mqtt->credentialsStored()) {
        break;

      } else if (!mqtt->connect()) {
        serverStatus = server::ServerStatus::SERVER_STATUS_CONNECT_TO_MQTT;

      } else {
        Serial.println("[Server] Server available");
        mqtt->subscribe(MQTT_COMMAND_RESTART, 0);
        mqtt->subscribe(MQTT_COMMAND_PING, 0);
        serverStatus = server::ServerStatus::SERVER_STATUS_AVAILABLE;
      }

      break;

    case server::ServerStatus::SERVER_STATUS_AVAILABLE:
      if (!mqtt->connected()) {
        Serial.println("[Server] MQTT lost, reconnecting");
        builtinLed->LightUp(false);
        serverStatus = server::ServerStatus::SERVER_STATUS_CONNECT_TO_MQTT;

      } else {
        builtinLed->LightUp(true);
        mqtt->loop();

        server::MqttMessage *message;
        while (xQueueReceive(MqttPublishingEventQueue, &message, 0) == pdPASS) {
          mqtt->publish(message);
          delete message;
        }
      }

      break;
    }

    vTaskDelay(pdMS_TO_TICKS(SERVER_TASK_DELAY_MS));
  }
}

void deviceStatsTask(void *pvParameters) {
  String datetime;

  for (;;) {
    if (sysClock->getCurrentTimeISO8601(&datetime)) {
      String jsonStats = stats->getStats(datetime);

      server::MqttMessage *message =
          new server::MqttMessage(MQTT_SUBJECT_DEVICE_STATS, jsonStats.c_str(),
                                  MQTT_SUBJECT_DEVICE_STATS_RETAINED);

      if (xQueueSend(MqttPublishingEventQueue, &message,
                     pdMS_TO_TICKS(MQTT_PUBLISHING_EVENT_QUEUE_DELAY_MS)) !=
          pdTRUE) {
        delete message;
      }

      vTaskDelay(pdMS_TO_TICKS(DEVICE_STATS_TASK_DELAY_MS));

    } else {
      vTaskDelay(pdMS_TO_TICKS(DEVICE_STATS_TASK_RETRY_DELAY_MS));
    }
  }
}

void restartDevice() { ESP.restart(); }

void ping() {
  server::MqttMessage *message = new server::MqttMessage(
      MQTT_SUBJECT_PING, nullptr, MQTT_SUBJECT_PING_RETAINED);
  if (xQueueSend(MqttPublishingEventQueue, &message,
                 pdMS_TO_TICKS(MQTT_PUBLISHING_EVENT_QUEUE_DELAY_MS)) != pdTRUE)
    delete message;
}

void commandNotSupported(const char *command) {
  String payload = String("Command not supported: ") + command;
  server::MqttMessage *message = new server::MqttMessage(
      MQTT_SUBJECT_ERROR, payload.c_str(), MQTT_SUBJECT_ERROR_RETAINED);
  if (xQueueSend(MqttPublishingEventQueue, &message,
                 pdMS_TO_TICKS(MQTT_PUBLISHING_EVENT_QUEUE_DELAY_MS)) != pdTRUE)
    delete message;
}

void controlTask(void *pvParameters) {
  for (;;) {
    server::MqttMessage *message;

    if (xQueueReceive(MqttSubscriptionsEventQueue, &message,
                      pdMS_TO_TICKS(MQTT_SUBSCRIPTIONS_QUEUE_DELAY_MS)) ==
        pdPASS) {
      if (strcmp(message->getSubject(), MQTT_COMMAND_RESTART) == 0) {
        restartDevice();

      } else if (strcmp(message->getSubject(), MQTT_COMMAND_PING) == 0) {
        ping();

      } else {
        commandNotSupported(message->getSubject());
      }

      delete message;
    }

    vTaskDelay(pdMS_TO_TICKS(CONTROL_TASK_DELAY_MS));
  }
}

void energySamplingTask(void *pvParameters) {
  String datetime;
  uint32_t lastSampleTime = millis() - DEFAULT_SAMPLING_INTERVAL_MILLISECONDS;

  for (;;) {
    bool samplingTimeReached =
        millis() - lastSampleTime >= DEFAULT_SAMPLING_INTERVAL_MILLISECONDS;

    if (samplingTimeReached && sysClock->getCurrentTimeISO8601(&datetime)) {
      lastSampleTime = millis();

      const String jsonEnergy = pzem->Read(datetime);
      Serial.println("[Energy Sampling] " + jsonEnergy);

      server::MqttMessage *message =
          new server::MqttMessage(MQTT_SUBJECT_ENERGY_STATS, jsonEnergy.c_str(),
                                  MQTT_SUBJECT_ENERGY_STATS_RETAINED);

      if (xQueueSend(MqttPublishingEventQueue, &message,
                     pdMS_TO_TICKS(MQTT_PUBLISHING_EVENT_QUEUE_DELAY_MS)) !=
          pdTRUE)
        delete message;

      vTaskDelay(pdMS_TO_TICKS(ENERGY_SAMPLING_TASK_DELAY_MS));

    } else {
      vTaskDelay(pdMS_TO_TICKS(ENERGY_SAMPLING_TASK_RETRY_DELAY_MS));
    }
  }
}

void setup() {
  Serial.begin(SERIAL_BAUD_RATE);
  Serial.println("[Setup] Initializing volttio");

  MqttPublishingEventQueue = xQueueCreate(MQTT_PUBLISHING_EVENT_QUEUE_SIZE,
                                          sizeof(server::MqttMessage *));
  MqttSubscriptionsEventQueue = xQueueCreate(MQTT_SUBSCRIPTIONS_QUEUE_SIZE,
                                             sizeof(server::MqttMessage *));

  sysClock = new board::Clock(NTP_SERVER, LOCAL_TIMEZONE_OFFSET_SEC,
                              LOCAL_DAYLIGHT_OFFSET_SEC);

  stats = new board::Stats();

  builtinLed = new peripherals::Led(BUILTIN_LED_PIN);
  builtinLed->LightUp(false);

  pzem = new peripherals::Pzem004t(PZEM_UART_RX_PIN, PZEM_UART_TX_PIN);

  wifi = new server::WifiService();

  {
    domain::FlashWriter mqttWriter(domain::FLASH_NAMESPACE_MQTT);
    mqttWriter.saveString(domain::FLASH_KEY_MQTT_DOMAIN, MQTT_SERVER_DEFAULT);
    mqttWriter.saveString(domain::FLASH_KEY_MQTT_USER, MQTT_USER_DEFAULT);
    mqttWriter.saveString(domain::FLASH_KEY_MQTT_PASSWORD, MQTT_PASSWORD_DEFAULT);
    mqttWriter.saveUint16(domain::FLASH_KEY_MQTT_PORT, MQTT_PORT_DEFAULT);
  }

  mqtt = new server::MqttService(PROJECT_NAME, DEVICE_ID,
                                MqttSubscriptionsEventQueue);

  serverStatus = server::ServerStatus::SERVER_STATUS_CONNECT_TO_WIFI;

  bleService = new ble::BleService(PROJECT_NAME, DEVICE_ID);
  bleService->start();

  xTaskCreatePinnedToCore(
      syncTimeTask, "syncTimeTask", SYNC_TIME_TASK_STACK_SIZE, nullptr,
      SYNC_TIME_TASK_PRIORITY, &syncTimeTaskHandle, SYNC_TIME_TASK_CORE);

  xTaskCreatePinnedToCore(serverTask, "serverTask", SERVER_TASK_STACK_SIZE,
                          nullptr, SERVER_TASK_PRIORITY, &serverTaskHandle,
                          SERVER_TASK_CORE);

  xTaskCreatePinnedToCore(deviceStatsTask, "deviceStatsTask",
                          DEVICE_STATS_TASK_STACK_SIZE, nullptr,
                          DEVICE_STATS_TASK_PRIORITY, &deviceStatsTaskHandle,
                          DEVICE_STATS_TASK_CORE);

  xTaskCreatePinnedToCore(controlTask, "controlTask", CONTROL_TASK_STACK_SIZE,
                          nullptr, CONTROL_TASK_PRIORITY, &controlTaskHandle,
                          CONTROL_TASK_CORE);

  xTaskCreatePinnedToCore(energySamplingTask, "energySamplingTask",
                          ENERGY_SAMPLING_TASK_STACK_SIZE, nullptr,
                          ENERGY_SAMPLING_TASK_PRIORITY,
                          &energySamplingTaskHandle, ENERGY_SAMPLING_TASK_CORE);

  Serial.println("[Setup] All tasks created");
}

void loop() {}

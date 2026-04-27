#pragma once

#include <Arduino.h>
#include <WiFi.h>
#include <PubSubClient.h>
#include <MajoMqtt.h>
#include <cstdint>

#include "connection.h"
#include "fibonacci.h"
#include "flash_memory.h"

namespace server {

extern const bool DEFAULT_MQTT_MESSAGE_RETAINED;

extern const uint8_t DEFAULT_MQTT_MESSAGE_QOS;

extern const char *DEFAULT_MQTT_TOPIC_SEPARATOR;

class MqttMessage {
private:
  String _subject;
  String _payload;

  const uint8_t _qos;
  const bool _retained;

public:
  MqttMessage(const char *subject, const char *payload,
              const bool retained = DEFAULT_MQTT_MESSAGE_RETAINED,
              const uint8_t qos = DEFAULT_MQTT_MESSAGE_QOS);

  ~MqttMessage() = default;

  const char *getSubject() const;

  const String &getPayload() const;

  const uint8_t getQos() const;

  const bool getRetained() const;
};

class MqttService : public domain::IConnectionHandler {
private:
  const char *_userKey;
  const char *_passwordKey;
  const char *_domainKey;
  const char *_portKey;
  domain::FlashReader *_flashReader;

  const char *_projectName;
  const char *_clientId;
  const char *_topicSeparator;

  WiFiClient _wifiClient;
  PubSubClient _pubSubClient;
  MajoMqtt<512, 512> _mqtt;

  QueueHandle_t _subscriptionQueue;

  // Static trampoline so we can set a raw PubSubClient callback that routes
  // messages to the subscription queue without requiring JSON payloads.
  static MqttService *_instance;
  static void _rawCallback(char *topic, byte *payload, unsigned int length);
  void _handleIncomingMessage(char *topic, byte *payload, unsigned int length);

  const char *getUserKey() const;

  const char *getPasswordKey() const;

  const char *getDomainKey() const;

  const char *getPortKey() const;

  domain::FlashReader *getFlashReader() const;

  const char *getProjectName() const;

  const char *getClientId() const;

  const char *getTopicSeparator() const;

  const String getBaseTopic() const;

  const String getTopic(const char *subject) const;

public:
  MqttService(const char *projectName, const char *clientId,
              QueueHandle_t subscriptionQueue,
              const char *userKey = domain::FLASH_KEY_MQTT_USER,
              const char *passwordKey = domain::FLASH_KEY_MQTT_PASSWORD,
              const char *domainKey = domain::FLASH_KEY_MQTT_DOMAIN,
              const char *portKey = domain::FLASH_KEY_MQTT_PORT);

  ~MqttService() override;

  bool credentialsStored();

  bool publish(MqttMessage *message);

  bool
  connect(uint8_t maxRetries = domain::DEFAULT_CONNECTION_MAX_RETRIES) override;

  bool connected() override;

  bool subscribe(const char *topic, uint8_t qos = DEFAULT_MQTT_MESSAGE_QOS);

  String getSubjectFromTopic(const char *fullTopic) const;

  // Must be called regularly when connected to process incoming messages.
  void loop();
};

} // namespace server

#include "ble.h"

#include <cstdlib>

#include "config.h"

namespace ble {

void BleConnectionCallbacks::onDisconnect(BLEServer *pServer) {
  Serial.println("[BLE] Client disconnected, restarting advertising");
  BLEDevice::startAdvertising();
}

BleStringCallbacks::BleStringCallbacks(domain::FlashWriter *flashWriter,
                                       const char *key)
    : _flashWriter(flashWriter), _key(key) {}

domain::FlashWriter *BleStringCallbacks::getFlashWriter() const {
  return _flashWriter;
}

const char *BleStringCallbacks::getKey() const { return _key; }

void BleStringCallbacks::onWrite(BLECharacteristic *pCharacteristic) {
  std::string value = pCharacteristic->getValue();
  this->getFlashWriter()->saveString(this->getKey(), value.c_str());
  Serial.printf("[BLE] Credential saved: %s\n", this->getKey());
}

BleUint16Callbacks::BleUint16Callbacks(domain::FlashWriter *flashWriter,
                                       const char *key)
    : _flashWriter(flashWriter), _key(key) {}

domain::FlashWriter *BleUint16Callbacks::getFlashWriter() const {
  return _flashWriter;
}

const char *BleUint16Callbacks::getKey() const { return _key; }

void BleUint16Callbacks::onWrite(BLECharacteristic *pCharacteristic) {
  std::string value = pCharacteristic->getValue();
  uint16_t port = static_cast<uint16_t>(atoi(value.c_str()));
  this->getFlashWriter()->saveUint16(this->getKey(), port);
  Serial.printf("[BLE] Credential saved: %s = %u\n", this->getKey(), port);
}

const char *BleService::getDeviceName() const { return _deviceName; }

const char *BleService::getServiceUuid() const { return _serviceUuid; }

domain::FlashWriter *BleService::getWifiWriter() const { return _wifiWriter; }

domain::FlashWriter *BleService::getMqttWriter() const { return _mqttWriter; }

BLEServer *BleService::getServer() const { return _server; }

void BleService::setServer(BLEServer *server) { _server = server; }

BleService::BleService(const char *deviceName, const char *serviceUuid)
    : _deviceName(deviceName), _serviceUuid(serviceUuid),
      _wifiWriter(new domain::FlashWriter(domain::FLASH_NAMESPACE_WIFI)),
      _mqttWriter(new domain::FlashWriter(domain::FLASH_NAMESPACE_MQTT)),
      _server(nullptr) {}

BleService::~BleService() {
  delete _wifiWriter;
  delete _mqttWriter;
}

bool BleService::start() {
  Serial.println("[BLE] Initializing BLE service");
  BLEDevice::init(this->getDeviceName());

  this->setServer(BLEDevice::createServer());
  /* BLE library does not take ownership of callbacks; they are never freed.
   * start() is intended to be called at most once (guarded by started()). */
  this->getServer()->setCallbacks(new BleConnectionCallbacks());

  ::BLEService *service =
      this->getServer()->createService(this->getServiceUuid());

  BLECharacteristic *wifiSsid = service->createCharacteristic(
      BLE_CHAR_WIFI_SSID_UUID, BLECharacteristic::PROPERTY_WRITE);
  wifiSsid->setCallbacks(new BleStringCallbacks(this->getWifiWriter(),
                                                domain::FLASH_KEY_WIFI_SSID));

  BLECharacteristic *wifiPass = service->createCharacteristic(
      BLE_CHAR_WIFI_PASSWORD_UUID, BLECharacteristic::PROPERTY_WRITE);
  wifiPass->setCallbacks(new BleStringCallbacks(
      this->getWifiWriter(), domain::FLASH_KEY_WIFI_PASSWORD));

  BLECharacteristic *mqttUser = service->createCharacteristic(
      BLE_CHAR_MQTT_USER_UUID, BLECharacteristic::PROPERTY_WRITE);
  mqttUser->setCallbacks(new BleStringCallbacks(this->getMqttWriter(),
                                                domain::FLASH_KEY_MQTT_USER));

  BLECharacteristic *mqttPass = service->createCharacteristic(
      BLE_CHAR_MQTT_PASSWORD_UUID, BLECharacteristic::PROPERTY_WRITE);
  mqttPass->setCallbacks(new BleStringCallbacks(
      this->getMqttWriter(), domain::FLASH_KEY_MQTT_PASSWORD));

  BLECharacteristic *mqttDomain = service->createCharacteristic(
      BLE_CHAR_MQTT_DOMAIN_UUID, BLECharacteristic::PROPERTY_WRITE);
  mqttDomain->setCallbacks(new BleStringCallbacks(
      this->getMqttWriter(), domain::FLASH_KEY_MQTT_DOMAIN));

  BLECharacteristic *mqttPort = service->createCharacteristic(
      BLE_CHAR_MQTT_PORT_UUID, BLECharacteristic::PROPERTY_WRITE);
  mqttPort->setCallbacks(new BleUint16Callbacks(this->getMqttWriter(),
                                                domain::FLASH_KEY_MQTT_PORT));

  service->start();

  BLEAdvertising *advertising = BLEDevice::getAdvertising();
  advertising->addServiceUUID(this->getServiceUuid());
  advertising->setScanResponse(true);
  advertising->start();

  Serial.println("[BLE] Advertising started");
  return true;
}

bool BleService::started() { return BLEDevice::getInitialized(); }

} // namespace ble

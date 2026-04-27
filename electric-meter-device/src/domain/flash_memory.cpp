#include "flash_memory.h"

namespace domain {

const char *FLASH_NAMESPACE_WIFI = "volttio_wifi";

const char *FLASH_NAMESPACE_MQTT = "volttio_mqtt";

const char *FLASH_KEY_WIFI_SSID = "wifi_ssid";

const char *FLASH_KEY_WIFI_PASSWORD = "wifi_pass";

const char *FLASH_KEY_MQTT_USER = "mqtt_user";

const char *FLASH_KEY_MQTT_PASSWORD = "mqtt_pass";

const char *FLASH_KEY_MQTT_DOMAIN = "mqtt_domain";

const char *FLASH_KEY_MQTT_PORT = "mqtt_port";

const char *FlashStorageBase::getNamespace() const { return _namespace; }

Preferences &FlashStorageBase::getPreferences() { return _preferences; }

FlashStorageBase::FlashStorageBase(const char *ns)
    : _namespace(ns), _preferences() {}

FlashWriter::FlashWriter(const char *ns) : FlashStorageBase(ns) {}

bool FlashWriter::saveString(const char *key, const char *value) {
  if (!this->getPreferences().begin(this->getNamespace(), false))
    return false;

  this->getPreferences().putString(key, value);
  this->getPreferences().end();

  return true;
}

bool FlashWriter::saveUint16(const char *key, const uint16_t value) {
  if (!this->getPreferences().begin(this->getNamespace(), false))
    return false;

  this->getPreferences().putUInt(key, value);
  this->getPreferences().end();

  return true;
}

FlashReader::FlashReader(const char *ns) : FlashStorageBase(ns) {}

const String FlashReader::readString(const char *key) {
  String defaultValue = "";

  if (!this->getPreferences().begin(this->getNamespace(), true))
    return defaultValue;

  String value = this->getPreferences().getString(key, defaultValue);
  this->getPreferences().end();

  return value;
}

uint16_t FlashReader::readUint16(const char *key) {
  uint16_t defaultValue = 0;

  if (!this->getPreferences().begin(this->getNamespace(), true))
    return defaultValue;

  uint16_t value = this->getPreferences().getUInt(key, defaultValue);
  this->getPreferences().end();

  return value;
}

} // namespace domain

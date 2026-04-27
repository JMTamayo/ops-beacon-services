#pragma once

#include <Preferences.h>

namespace domain {

extern const char *FLASH_NAMESPACE_WIFI;

extern const char *FLASH_NAMESPACE_MQTT;

extern const char *FLASH_KEY_WIFI_SSID;

extern const char *FLASH_KEY_WIFI_PASSWORD;

extern const char *FLASH_KEY_MQTT_USER;

extern const char *FLASH_KEY_MQTT_PASSWORD;

extern const char *FLASH_KEY_MQTT_DOMAIN;

extern const char *FLASH_KEY_MQTT_PORT;

class FlashStorageBase {
protected:
  const char *_namespace;
  Preferences _preferences;

  const char *getNamespace() const;

  Preferences &getPreferences();

  FlashStorageBase(const char *ns);

  virtual ~FlashStorageBase() = default;

public:
  FlashStorageBase(const FlashStorageBase &) = delete;

  FlashStorageBase &operator=(const FlashStorageBase &) = delete;
};

class FlashWriter : public FlashStorageBase {
public:
  FlashWriter(const char *ns);

  bool saveString(const char *key, const char *value);

  bool saveUint16(const char *key, const uint16_t value);
};

class FlashReader : public FlashStorageBase {
public:
  FlashReader(const char *ns);

  const String readString(const char *key);

  uint16_t readUint16(const char *key);
};

} // namespace domain

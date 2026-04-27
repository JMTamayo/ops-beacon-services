#include "wifi_.h"

#include <cstdint>

#include "secrets.h"

namespace server {

const char *WifiService::getSsidKey() const { return _ssidKey; }

const char *WifiService::getPasswordKey() const { return _passwordKey; }

domain::FlashReader *WifiService::getFlashReader() const {
  return _flashReader;
}

WifiService::WifiService(const char *ssidKey, const char *passwordKey)
    : _ssidKey(ssidKey), _passwordKey(passwordKey),
      _flashReader(new domain::FlashReader(domain::FLASH_NAMESPACE_WIFI)) {}

WifiService::~WifiService() { delete _flashReader; }

bool WifiService::credentialsStored() {
  String ssid = this->getFlashReader()->readString(this->getSsidKey());
  if (!ssid.isEmpty()) return true;
#ifdef WIFI_SSID_DEFAULT
  return strlen(WIFI_SSID_DEFAULT) > 0;
#else
  return false;
#endif
}

bool WifiService::connect(const uint8_t maxRetries) {
  String ssid = this->getFlashReader()->readString(this->getSsidKey());
  String pass = this->getFlashReader()->readString(this->getPasswordKey());

  if (ssid.isEmpty()) {
#ifdef WIFI_SSID_DEFAULT
    Serial.println("[WiFi] No stored credentials, using defaults from secrets.h");
    ssid = WIFI_SSID_DEFAULT;
    pass = WIFI_PASSWORD_DEFAULT;
#endif
  }

  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, pass);

  uint8_t retries = 0;

  while (!this->connected()) {
    if (retries > maxRetries) {
      Serial.println("[WiFi] Connection failed, max retries reached");
      return false;
    }

    uint32_t delayMs = domain::Fibonacci::get(retries) * 1000;
    vTaskDelay(pdMS_TO_TICKS(delayMs));

    retries++;
  }

  Serial.printf("[WiFi] Connected, IP: %s\n",
                WiFi.localIP().toString().c_str());
  return true;
}

bool WifiService::connected() { return WiFi.status() == WL_CONNECTED; }

} // namespace server

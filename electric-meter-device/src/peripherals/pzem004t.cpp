#include "pzem004t.h"

#include <Arduino.h>
#include <ArduinoJson.h>

namespace peripherals {

const uint8_t Pzem004t::getRxPin() const { return _rxPin; }

const uint8_t Pzem004t::getTxPin() const { return _txPin; }

Pzem004t::Pzem004t(const uint8_t rxPin, const uint8_t txPin)
    : _rxPin(rxPin), _txPin(txPin), _pzem(Serial2, rxPin, txPin) {}

String Pzem004t::Read(const String &currentTime) {
  const float voltage = _pzem.voltage();
  const float current = _pzem.current();
  const float power = _pzem.power();
  const float energyKwh = _pzem.energy();
  const float frequency = _pzem.frequency();
  const float powerFactor = _pzem.pf();

  JsonDocument doc;

  doc["local_timestamptz"] = currentTime;

  JsonObject data = doc["data"].to<JsonObject>();

  if (std::isnan(voltage))
    data["voltage"] = nullptr;
  else
    data["voltage"] = voltage;

  if (std::isnan(current))
    data["current"] = nullptr;
  else
    data["current"] = current;

  if (std::isnan(power))
    data["active_power"] = nullptr;
  else
    data["active_power"] = power;

  if (std::isnan(energyKwh))
    data["active_energy"] = nullptr;
  else
    data["active_energy"] = energyKwh;

  if (std::isnan(frequency))
    data["frequency"] = nullptr;
  else
    data["frequency"] = frequency;

  if (std::isnan(powerFactor))
    data["power_factor"] = nullptr;
  else {
    data["power_factor"] = powerFactor;
  }

  String jsonString;
  serializeJson(doc, jsonString);
  return jsonString;
}

} // namespace peripherals

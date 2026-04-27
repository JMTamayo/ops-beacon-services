#pragma once

#include <Arduino.h>
#include <PZEM004Tv30.h>
#include <cstdint>

namespace peripherals {

class Pzem004t {
private:
  const uint8_t _rxPin;
  const uint8_t _txPin;
  PZEM004Tv30 _pzem;

  const uint8_t getRxPin() const;
  const uint8_t getTxPin() const;

public:
  Pzem004t(const uint8_t rxPin, const uint8_t txPin);

  ~Pzem004t() = default;

  String Read(const String &currentTime);
};

} // namespace peripherals

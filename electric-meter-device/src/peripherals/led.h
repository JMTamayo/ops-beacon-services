#pragma once

#include <Arduino.h>

namespace peripherals {

class Led {
private:
  const uint8_t pin;

  const uint8_t getPin() const;

public:
  Led(const uint8_t pin);

  ~Led() = default;

  void LightUp(bool on);
};

} // namespace peripherals
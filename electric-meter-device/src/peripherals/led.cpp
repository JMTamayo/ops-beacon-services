#include "led.h"

namespace peripherals {

const uint8_t Led::getPin() const { return this->pin; }

Led::Led(const uint8_t pin) : pin(pin) {
  pinMode(this->getPin(), OUTPUT);
  digitalWrite(this->getPin(), LOW);
}

void Led::LightUp(bool on) { digitalWrite(this->getPin(), on ? HIGH : LOW); }

} // namespace peripherals
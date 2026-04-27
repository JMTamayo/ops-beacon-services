#pragma once

#include <Arduino.h>
#include <ArduinoJson.h>
#include <cstdint>
#include <esp_system.h>

namespace board {

class Stats {
private:
  uint32_t _lastMillis{0};
  uint32_t _overflowCount{0};

  uint32_t getLastMillis() const;

  void setLastMillis(uint32_t lastMillis);

  uint32_t getOverflowCount() const;

  void incrementOverflowCount();

  const char *resetReasonDescription(esp_reset_reason_t reason) const;

public:
  Stats();

  ~Stats() = default;

  String getStats(const String &currentTime);

  uint64_t getUptimeMs();
};

} // namespace board
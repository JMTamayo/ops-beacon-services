#include "stats.h"

namespace board {

const char *Stats::resetReasonDescription(esp_reset_reason_t reason) const {
  switch (reason) {
  case ESP_RST_POWERON:
    return "Power-on reset";
  case ESP_RST_EXT:
    return "External reset (pin)";
  case ESP_RST_SW:
    return "Software reset (esp_restart)";
  case ESP_RST_PANIC:
    return "Exception or panic";
  case ESP_RST_INT_WDT:
    return "Interrupt watchdog";
  case ESP_RST_TASK_WDT:
    return "Task watchdog";
  case ESP_RST_WDT:
    return "Other watchdog";
  case ESP_RST_DEEPSLEEP:
    return "Wake from deep sleep";
  case ESP_RST_BROWNOUT:
    return "Brownout (low voltage)";
  case ESP_RST_SDIO:
    return "SDIO reset";
  default:
    return "Unknown";
  }
}

uint32_t Stats::getLastMillis() const { return _lastMillis; }

void Stats::setLastMillis(uint32_t lastMillis) { _lastMillis = lastMillis; }

uint32_t Stats::getOverflowCount() const { return _overflowCount; }

void Stats::incrementOverflowCount() { this->_overflowCount++; }

Stats::Stats() : _lastMillis(millis()), _overflowCount(0) {}

uint64_t Stats::getUptimeMs() {
  const uint32_t now = millis();
  if (now < this->getLastMillis())
    this->incrementOverflowCount();
  this->setLastMillis(now);
  return (uint64_t)this->getOverflowCount() * (1ULL << 32) + now;
}

String Stats::getStats(const String &currentTime) {
  const uint32_t flashTotal = ESP.getFlashChipSize();
  const uint32_t flashFree = ESP.getFreeSketchSpace();
  const uint32_t sketchSize = ESP.getSketchSize();
  const uint32_t heapTotal = ESP.getHeapSize();
  const uint32_t heapFree = ESP.getFreeHeap();
  const uint32_t heapMaxAlloc = ESP.getMaxAllocHeap();
  const uint32_t heapMinFree = ESP.getMinFreeHeap();
  const esp_reset_reason_t resetReason = esp_reset_reason();
  const uint64_t uptimeMs = getUptimeMs();

  JsonDocument doc;

  doc["local_timestamptz"] = currentTime;

  JsonObject data = doc["data"].to<JsonObject>();

  JsonObject uptime = data["uptime"].to<JsonObject>();
  uptime["milliseconds"] = uptimeMs;

  JsonObject reset_reason = data["last_reset_reason"].to<JsonObject>();
  reset_reason["code"] = static_cast<int>(resetReason);
  reset_reason["description"] = resetReasonDescription(resetReason);

  JsonObject ram = data["ram"].to<JsonObject>();
  ram["total_bytes"] = heapTotal;
  ram["free_bytes"] = heapFree;
  ram["max_alloc_bytes"] = heapMaxAlloc;
  ram["min_free_bytes"] = heapMinFree;

  JsonObject flash = data["flash"].to<JsonObject>();
  flash["total_bytes"] = flashTotal;
  flash["free_bytes"] = flashFree;
  flash["sketch_bytes"] = sketchSize;

  String jsonString;
  serializeJson(doc, jsonString);

  return jsonString;
}

} // namespace board
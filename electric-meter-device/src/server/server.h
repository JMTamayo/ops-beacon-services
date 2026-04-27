#pragma once

#include <cstdint>

namespace server {

enum class ServerStatus : uint8_t {
  SERVER_STATUS_CONNECT_TO_WIFI = 0,
  SERVER_STATUS_CONNECT_TO_MQTT = 1,
  SERVER_STATUS_AVAILABLE = 2,
};

} // namespace server

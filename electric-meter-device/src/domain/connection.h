#pragma once

#include <cstdint>

namespace domain {

const uint8_t DEFAULT_CONNECTION_MAX_RETRIES = 6;

class IConnectionHandler {

public:
  virtual ~IConnectionHandler() = default;

  virtual bool
  connect(const uint8_t maxRetries = DEFAULT_CONNECTION_MAX_RETRIES) = 0;

  virtual bool connected() = 0;
};

} // namespace domain

#pragma once

#include <Arduino.h>
#include <time.h>

namespace board {

class Clock {
private:
  const char *_ntpServer;
  const int _localTimezoneOffsetSec;
  const int _localDaylightOffsetSec;

  const char *getNtpServer() const;

  const int getLocalTimezoneOffsetSec() const;

  const int getLocalDaylightOffsetSec() const;

public:
  Clock(const char *ntpServer, const int localTimezoneOffsetSec,
        const int localDaylightOffsetSec);

  ~Clock() = default;

  void syncTime();

  bool getCurrentTimeISO8601(String *datetime);
};

} // namespace board
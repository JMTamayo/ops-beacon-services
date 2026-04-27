#include "clock.h"

namespace board {

const char *Clock::getNtpServer() const { return this->_ntpServer; }

const int Clock::getLocalTimezoneOffsetSec() const {
  return this->_localTimezoneOffsetSec;
}

const int Clock::getLocalDaylightOffsetSec() const {
  return this->_localDaylightOffsetSec;
}

Clock::Clock(const char *ntpServer, const int localTimezoneOffsetSec,
             const int localDaylightOffsetSec)
    : _ntpServer(ntpServer), _localTimezoneOffsetSec(localTimezoneOffsetSec),
      _localDaylightOffsetSec(localDaylightOffsetSec) {}

void Clock::syncTime() {
  configTime(this->getLocalTimezoneOffsetSec(),
             this->getLocalDaylightOffsetSec(), this->getNtpServer());
}

bool Clock::getCurrentTimeISO8601(String *datetime) {
  struct timeval tv;
  if (gettimeofday(&tv, nullptr) != 0)
    return false;

  struct tm timeinfo;
  if (localtime_r(&tv.tv_sec, &timeinfo) == nullptr)
    return false;

  if (timeinfo.tm_year < 100)
    return false;

  const long ms = (tv.tv_usec / 1000) % 1000;
  const int offset_sec = this->getLocalTimezoneOffsetSec();
  const int tz_h = offset_sec / 3600;
  const int tz_m = (abs(offset_sec) % 3600) / 60;

  char buffer[32];
  size_t n = strftime(buffer, sizeof(buffer), "%Y-%m-%dT%H:%M:%S", &timeinfo);
  snprintf(buffer + n, sizeof(buffer) - n, ".%03ld%+03d%02d", ms, tz_h, tz_m);
  *datetime = String(buffer);

  return true;
}

} // namespace board
#include "fibonacci.h"

namespace domain {

uint32_t Fibonacci::get(const uint32_t n) {
  if (n <= 1)
    return n;

  uint32_t prev = 0;
  uint32_t curr = 1;

  for (uint32_t i = 2; i <= n; i++) {
    uint32_t next = prev + curr;
    prev = curr;
    curr = next;
  }

  return curr;
}

} // namespace domain

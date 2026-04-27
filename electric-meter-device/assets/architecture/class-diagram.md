# Class Diagram

Class and interface relationships in `alpha`, **split by source folder** (`src/domain`, `src/server`, etc.) so each diagram stays easy to read. Types from other modules appear as stubs or notes where a relationship must be shown.

**Rendering note:** Mermaid parses `<<`…`>>` as stereotypes. Avoid spaces, `+`, `/`, or long text inside them (that can split `<<` / `>>` in the UI). Details go in `note for ClassName "..."` lines instead.

---

## `src/domain`

Connection contract, NVS helpers, and retry backoff.

```mermaid
classDiagram
class IConnectionHandler {
  <<interface>>
  +connect(maxRetries) bool
  +connected() bool
}

class Fibonacci {
  <<utility>>
  +get(n) uint32_t
}

note for Fibonacci "static method (see fibonacci.cpp)"

class FlashStorageBase {
  #_namespace: const char*
  #_preferences: Preferences
}

class FlashWriter {
  +saveString(key, value) bool
  +saveUint16(key, value) bool
}

class FlashReader {
  +readString(key) String
  +readUint16(key) uint16_t
}

FlashStorageBase <|-- FlashWriter
FlashStorageBase <|-- FlashReader
```

---

## `src/server`

WiFi/MQTT services, MQTT DTO, and `ServerStatus`. `WifiService` and `MqttService` implement `IConnectionHandler` from `domain`; both use `FlashReader` for credentials.

```mermaid
classDiagram
class IConnectionHandler {
  <<interface>>
  +connect(maxRetries) bool
  +connected() bool
}

note for IConnectionHandler "Defined in domain namespace"

class ServerStatus {
  <<enum>>
  SERVER_STATUS_CONNECT_TO_WIFI
  SERVER_STATUS_CONNECT_TO_MQTT
  SERVER_STATUS_AVAILABLE
}

class MqttMessage {
  -_subject: String
  -_payload: String
  -_qos: uint8_t
  -_retained: bool
  +getSubject() const char*
  +getPayload() const String&
}

class WifiService {
  -_flashReader: FlashReader*
  +credentialsStored() bool
  +connect(maxRetries) bool
  +connected() bool
}

class MqttService {
  -_flashReader: FlashReader*
  -_client: AsyncMqttClient&
  -_subscriptionQueue: QueueHandle_t
  +credentialsStored() bool
  +publish(message) bool
  +connect(maxRetries) bool
  +connected() bool
  +subscribe(topic, qos) bool
}

class FlashReader {
  <<stub>>
}

note for FlashReader "domain::FlashReader (credentials in NVS)"

IConnectionHandler <|-- WifiService
IConnectionHandler <|-- MqttService
WifiService --> FlashReader
MqttService --> FlashReader
MqttService ..> MqttMessage : publish
```

---

## `src/ble`

BLE provisioning server and characteristic callbacks. Callbacks write credentials through `FlashWriter` (`domain`).

```mermaid
classDiagram
class BleConnectionCallbacks {
  <<callback>>
  +onDisconnect(pServer) void
}

note for BleConnectionCallbacks "extends Arduino BLEServerCallbacks"

class BleStringCallbacks {
  <<callback>>
  -_flashWriter: FlashWriter*
  -_key: const char*
  +onWrite(pCharacteristic) void
}

note for BleStringCallbacks "extends Arduino BLECharacteristicCallbacks"

class BleUint16Callbacks {
  <<callback>>
  -_flashWriter: FlashWriter*
  -_key: const char*
  +onWrite(pCharacteristic) void
}

note for BleUint16Callbacks "extends Arduino BLECharacteristicCallbacks"

class BleService {
  -_deviceName: const char*
  -_serviceUuid: const char*
  -_wifiWriter: FlashWriter*
  -_mqttWriter: FlashWriter*
  -_server: BLEServer*
  +start() bool
  +started() bool
}

class FlashWriter {
  <<stub>>
}

note for FlashWriter "domain::FlashWriter (NVS writes from BLE)"

BleService --> BleConnectionCallbacks
BleService --> BleStringCallbacks
BleService --> BleUint16Callbacks
BleStringCallbacks --> FlashWriter
BleUint16Callbacks --> FlashWriter
```

---

## `src/board`

Device clock (NTP) and JSON device statistics.

```mermaid
classDiagram
class Clock {
  +syncTime() void
  +getCurrentTimeISO8601(datetime) bool
}

class Stats {
  +getStats(currentTime) String
  +getUptimeMs() uint64_t
}
```

---

## `src/peripherals`

Onboard LED and PZEM-004T wrapper around the vendor library type.

```mermaid
classDiagram
class Led {
  -pin: uint8_t
  +LightUp(on) void
}

class Pzem004t {
  -_rxPin: uint8_t
  -_txPin: uint8_t
  -_pzem: PZEM004Tv30
  +Read(currentTime) String
}

class PZEM004Tv30 {
  <<external>>
}

note for PZEM004Tv30 "Dependency: mandulaj/PZEM-004T-v30 (PlatformIO)"

Pzem004t *-- PZEM004Tv30
```

---

## `src/main.cpp` (runtime wiring)

Global orchestration: tasks, queues, and owned service pointers.

```mermaid
classDiagram
class MainRuntime {
  <<runtime>>
  +setup()
  +loop()
  +serverTask()
  +controlTask()
  +deviceStatsTask()
  +energySamplingTask()
  +syncTimeTask()
}

note for MainRuntime "Not a C++ class: global setup + task entry points"

class ServerStatus {
  <<enum>>
}

note for ServerStatus "server::ServerStatus"

class QueuePublishing {
  <<handle>>
  MqttPublishingEventQueue
}

note for QueuePublishing "FreeRTOS QueueHandle_t"

class QueueSubscriptions {
  <<handle>>
  MqttSubscriptionsEventQueue
}

note for QueueSubscriptions "FreeRTOS QueueHandle_t"

class Clock {
  <<stub>>
}

note for Clock "board::Clock"

class Stats {
  <<stub>>
}

note for Stats "board::Stats"

class Led {
  <<stub>>
}

note for Led "peripherals::Led"

class Pzem004t {
  <<stub>>
}

note for Pzem004t "peripherals::Pzem004t"

class WifiService {
  <<stub>>
}

note for WifiService "server::WifiService"

class MqttService {
  <<stub>>
}

note for MqttService "server::MqttService"

class BleService {
  <<stub>>
}

note for BleService "ble::BleService"

MainRuntime --> Clock
MainRuntime --> Stats
MainRuntime --> Led
MainRuntime --> Pzem004t
MainRuntime --> WifiService
MainRuntime --> MqttService
MainRuntime --> BleService
MainRuntime --> ServerStatus
MainRuntime --> QueuePublishing
MainRuntime --> QueueSubscriptions
MqttService ..> QueueSubscriptions : incoming msgs
```

---

## Module dependency overview

How source folders depend on each other (not every class shown). **`main.cpp` does not include or reference `domain/` directly**; it only pulls in `board`, `ble`, `peripherals`, and `server` headers. The `domain` module is used inside `ble` and `server`.

```mermaid
flowchart LR
  subgraph main["main.cpp"]
    M[Orchestration]
  end

  subgraph board["board"]
    B[Clock, Stats]
  end

  subgraph ble["ble"]
    BL[BleService]
  end

  subgraph domain["domain"]
    D[IConnectionHandler, Flash*, Fibonacci]
  end

  subgraph peripherals["peripherals"]
    P[Led, Pzem004t]
  end

  subgraph server["server"]
    S[WifiService, MqttService, ServerStatus]
  end

  M --> board
  M --> ble
  M --> peripherals
  M --> server
  ble --> domain
  server --> domain
```

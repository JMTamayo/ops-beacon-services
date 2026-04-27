#include "mqtt.h"

namespace server {

const bool DEFAULT_MQTT_MESSAGE_RETAINED = false;

const uint8_t DEFAULT_MQTT_MESSAGE_QOS = 0;

const char *DEFAULT_MQTT_TOPIC_SEPARATOR = "/";

MqttService *MqttService::_instance = nullptr;

// ---------------------------------------------------------------------------
// MqttMessage
// ---------------------------------------------------------------------------

MqttMessage::MqttMessage(const char *subject, const char *payload,
                         const bool retained, const uint8_t qos)
    : _subject(subject != nullptr ? subject : ""),
      _payload(payload != nullptr ? payload : ""), _qos(qos),
      _retained(retained) {}

const char *MqttMessage::getSubject() const { return _subject.c_str(); }

const String &MqttMessage::getPayload() const { return _payload; }

const uint8_t MqttMessage::getQos() const { return _qos; }

const bool MqttMessage::getRetained() const { return _retained; }

// ---------------------------------------------------------------------------
// MqttService — private accessors
// ---------------------------------------------------------------------------

const char *MqttService::getUserKey() const { return _userKey; }

const char *MqttService::getPasswordKey() const { return _passwordKey; }

const char *MqttService::getDomainKey() const { return _domainKey; }

const char *MqttService::getPortKey() const { return _portKey; }

domain::FlashReader *MqttService::getFlashReader() const {
  return _flashReader;
}

const char *MqttService::getProjectName() const { return _projectName; }

const char *MqttService::getClientId() const { return _clientId; }

const char *MqttService::getTopicSeparator() const { return _topicSeparator; }

const String MqttService::getBaseTopic() const {
  return String(getTopicSeparator()) + String(getProjectName()) +
         String(getTopicSeparator()) + String(getClientId()) +
         String(getTopicSeparator());
}

const String MqttService::getTopic(const char *subject) const {
  return String(getBaseTopic()) + String(subject);
}

// ---------------------------------------------------------------------------
// MqttService — incoming message routing
//
// PubSubClient requires a plain function pointer for its callback.
// _rawCallback is the static trampoline that forwards to the active instance.
// This bypasses MajoMqtt's JSON-only routing so commands can arrive as
// plain-text or empty payloads, preserving VOLTTIO's topic-based command API.
// ---------------------------------------------------------------------------

void MqttService::_rawCallback(char *topic, byte *payload,
                                unsigned int length) {
  if (_instance)
    _instance->_handleIncomingMessage(topic, payload, length);
}

void MqttService::_handleIncomingMessage(char *topic, byte *payload,
                                          unsigned int length) {
  if (_subscriptionQueue == nullptr)
    return;

  String payloadStr = "";
  if (payload != nullptr && length > 0)
    payloadStr = String(reinterpret_cast<char *>(payload), length);

  String subject = getSubjectFromTopic(topic);
  MqttMessage *msg = new MqttMessage(subject.c_str(), payloadStr.c_str());
  if (xQueueSend(_subscriptionQueue, &msg, pdMS_TO_TICKS(10)) != pdPASS)
    delete msg;
}

// ---------------------------------------------------------------------------
// MqttService — constructor / destructor
// ---------------------------------------------------------------------------

MqttService::MqttService(const char *projectName, const char *clientId,
                         QueueHandle_t subscriptionQueue,
                         const char *userKey, const char *passwordKey,
                         const char *domainKey, const char *portKey)
    : _userKey(userKey), _passwordKey(passwordKey), _domainKey(domainKey),
      _portKey(portKey),
      _flashReader(new domain::FlashReader(domain::FLASH_NAMESPACE_MQTT)),
      _projectName(projectName), _clientId(clientId),
      _topicSeparator(DEFAULT_MQTT_TOPIC_SEPARATOR),
      _pubSubClient(_wifiClient),
      _mqtt(_pubSubClient),
      _subscriptionQueue(subscriptionQueue) {
  _instance = this;
  // Override MajoMqtt's static callback with our raw handler so incoming
  // messages are routed without requiring a JSON payload.
  _pubSubClient.setCallback(_rawCallback);
}

MqttService::~MqttService() {
  delete _flashReader;
  if (_instance == this)
    _instance = nullptr;
}

// ---------------------------------------------------------------------------
// MqttService — public API
// ---------------------------------------------------------------------------

bool MqttService::credentialsStored() {
  String user = getFlashReader()->readString(getUserKey());
  String domain = getFlashReader()->readString(getDomainKey());
  uint16_t port = getFlashReader()->readUint16(getPortKey());
  return !user.isEmpty() && !domain.isEmpty() && port > 0;
}

bool MqttService::publish(MqttMessage *message) {
  if (message == nullptr)
    return false;

  String topic = getTopic(message->getSubject());
  const String &payload = message->getPayload();
  const char *payloadPtr = payload.isEmpty() ? nullptr : payload.c_str();

  return _pubSubClient.publish(topic.c_str(), payloadPtr,
                               message->getRetained());
}

bool MqttService::connect(const uint8_t maxRetries) {
  String user = getFlashReader()->readString(getUserKey());
  String password = getFlashReader()->readString(getPasswordKey());
  String domain = getFlashReader()->readString(getDomainKey());
  uint16_t port = getFlashReader()->readUint16(getPortKey());

  Serial.printf("[MQTT] Connecting to %s:%u as %s\n", domain.c_str(), port,
                user.c_str());

  _mqtt.setServer(domain.c_str(), port);
  _mqtt.setClientId(getClientId());

  uint8_t retries = 0;
  while (retries <= maxRetries) {
    if (_pubSubClient.connect(getClientId(), user.c_str(), password.c_str())) {
      Serial.printf("[MQTT] Connected, client: %s\n", getClientId());
      return true;
    }

    if (retries == maxRetries)
      break;

    uint32_t delayMs = domain::Fibonacci::get(retries) * 1000;
    vTaskDelay(pdMS_TO_TICKS(delayMs));
    retries++;
  }

  Serial.println("[MQTT] Connection failed, max retries reached");
  return false;
}

bool MqttService::connected() { return _pubSubClient.connected(); }

bool MqttService::subscribe(const char *topic, uint8_t qos) {
  if (topic == nullptr || topic[0] == '\0')
    return false;
  String fullTopic = getTopic(topic);
  return _pubSubClient.subscribe(fullTopic.c_str(), qos);
}

String MqttService::getSubjectFromTopic(const char *fullTopic) const {
  if (fullTopic == nullptr || fullTopic[0] == '\0')
    return String("");

  String topicStr(fullTopic);
  topicStr.trim();

  String base = getBaseTopic();
  String subject;

  if (topicStr.startsWith(base)) {
    subject = topicStr.substring(base.length());
  } else {
    int lastSlash = topicStr.lastIndexOf('/');
    if (lastSlash >= 0 && lastSlash < (int)topicStr.length() - 1)
      subject = topicStr.substring(lastSlash + 1);
    else
      subject = topicStr;
  }

  subject.trim();
  return subject;
}

void MqttService::loop() {
  // Drive PubSubClient's internal state machine to process incoming messages.
  // Reconnection is intentionally left to the serverTask state machine so
  // credentials from NVS are always used.
  _pubSubClient.loop();
}

} // namespace server

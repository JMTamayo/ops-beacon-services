#pragma once

#include <BLECharacteristic.h>
#include <BLEDevice.h>
#include <BLEServer.h>

#include "flash_memory.h"

namespace ble {

class BleConnectionCallbacks : public BLEServerCallbacks {
public:
  void onDisconnect(BLEServer *pServer) override;
};

class BleStringCallbacks : public BLECharacteristicCallbacks {
private:
  domain::FlashWriter *_flashWriter;
  const char *_key;

  domain::FlashWriter *getFlashWriter() const;

  const char *getKey() const;

public:
  BleStringCallbacks(domain::FlashWriter *flashWriter, const char *key);

  void onWrite(BLECharacteristic *pCharacteristic) override;
};

class BleUint16Callbacks : public BLECharacteristicCallbacks {
private:
  domain::FlashWriter *_flashWriter;
  const char *_key;

  domain::FlashWriter *getFlashWriter() const;

  const char *getKey() const;

public:
  BleUint16Callbacks(domain::FlashWriter *flashWriter, const char *key);

  void onWrite(BLECharacteristic *pCharacteristic) override;
};

class BleService {
private:
  const char *_deviceName;
  const char *_serviceUuid;

  domain::FlashWriter *_wifiWriter;
  domain::FlashWriter *_mqttWriter;

  BLEServer *_server;

  const char *getDeviceName() const;

  const char *getServiceUuid() const;

  domain::FlashWriter *getWifiWriter() const;

  domain::FlashWriter *getMqttWriter() const;

  BLEServer *getServer() const;

  void setServer(BLEServer *server);

public:
  BleService(const char *deviceName, const char *serviceUuid);

  ~BleService();

  bool start();

  bool started();
};

} // namespace ble

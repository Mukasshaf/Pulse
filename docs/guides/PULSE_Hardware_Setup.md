# Pulse — Phase 2 Hardware Setup Guide

Follow this in order. Do not skip the I2C scanner step — it isolates wiring problems before you add firmware complexity on top.

---

## 1. Parts checklist

| Part | Qty | Notes |
|---|---|---|
| ESP32 DevKit (v1 or similar) | 1 | Any ESP32 dev board with exposed GPIO21/22/34 |
| MAX30102 breakout | 1 | PPG — usually sold with onboard 3.3V regulator + pull-ups |
| Grove-GSR sensor | 1 | 2 finger electrodes |
| MPU6050 breakout | 1 | Onboard pull-ups usually present |
| TP4056 charging module | 1 | Not wired this phase — see Section 6 |
| Breadboard + jumper wires | — | |
| USB cable (data-capable, not charge-only) | 1 | For programming + serial monitor |
| Multimeter | 1 | For continuity checks before power-on |

---

## 2. Before you touch anything — safety checklist

- **Power off / USB unplugged** while wiring. Never wire live.
- **Check ESP32 ADC pins are 3.3V-only.** GPIO34 cannot tolerate 5V. If your Grove-GSR module is powered at 5V, its output can exceed 3.3V and damage the ESP32 ADC input. Power Grove-GSR from the ESP32 **3V3** pin, not 5V/VIN.
- **Use a multimeter continuity check** on every GND-to-GND connection before first power-on. A missed ground is the single most common cause of "nothing works" on a first bring-up.
- Do not wire the TP4056/LiPo yet (Section 6 explains why).

---

## 3. Wiring — full pin table

All modules share GND with the ESP32 GND pin — wire this first for every module before anything else.

### 3.1 MAX30102 (I2C)

| MAX30102 pin | ESP32 pin | Notes |
|---|---|---|
| VIN | 3V3 | |
| GND | GND | |
| SCL | GPIO22 | Shared I2C clock line |
| SDA | GPIO21 | Shared I2C data line |
| INT | not connected | Not used — we poll instead of using interrupts |

### 3.2 MPU6050 (I2C, shares the bus with MAX30102)

| MPU6050 pin | ESP32 pin | Notes |
|---|---|---|
| VCC | 3V3 | |
| GND | GND | |
| SCL | GPIO22 | Same physical wire/rail as MAX30102 SCL |
| SDA | GPIO21 | Same physical wire/rail as MAX30102 SDA |
| AD0 | GND | Forces I2C address to 0x68 (default). Leave floating only if your breakout has an onboard pulldown — wiring it explicitly is safer. |

**Why sharing works:** MAX30102 defaults to I2C address `0x57`, MPU6050 to `0x68` — no address collision, so both can sit on the same two wires (SDA/SCL) without a multiplexer. Most breakout boards already carry onboard 4.7kΩ pull-up resistors; with only two devices on the bus you shouldn't need external pull-ups. If the I2C scan in Section 4 comes back empty, that's the first thing to add.

### 3.3 Grove-GSR (analog)

| Grove-GSR pin | ESP32 pin | Notes |
|---|---|---|
| SIG | GPIO34 | ADC1_CH6 — input-only pin, safe for analogRead |
| VCC | 3V3 | Powering at 3.3V (not 5V) keeps output within ADC-safe range |
| GND | GND | |

**Do not use GPIO35+ ADC2 pins for this** — ADC2 shares hardware with the ESP32's Wi-Fi radio and becomes unreliable if Wi-Fi is ever active. GPIO34 is ADC1 — safe regardless of Wi-Fi state, and this matters later if you add wireless logging.

---

## 4. Step 1 — verify I2C bus before writing any sensor code

Wire only MAX30102 + MPU6050 first (skip GSR for this step). Flash this sketch:

```cpp
#include <Wire.h>

void setup() {
  Wire.begin(21, 22);  // SDA, SCL
  Serial.begin(115200);
  delay(1000);
  Serial.println("I2C Scanner starting...");
}

void loop() {
  byte count = 0;
  for (byte addr = 1; addr < 127; addr++) {
    Wire.beginTransmission(addr);
    byte error = Wire.endTransmission();
    if (error == 0) {
      Serial.print("Found device at 0x");
      if (addr < 16) Serial.print("0");
      Serial.println(addr, HEX);
      count++;
    }
  }
  if (count == 0) Serial.println("No I2C devices found — check wiring");
  Serial.println("---");
  delay(3000);
}
```

**Expected output:**
```
Found device at 0x57
Found device at 0x68
---
```

If you see both addresses, wiring is correct — proceed to Section 5. If you see neither, **stop and troubleshoot here** (see Section 7) before adding anything else. Debugging is far easier with two devices and no other code in play than with the full firmware running.

---

## 5. Step 2 — full firmware

Once the I2C scan passes, wire in the Grove-GSR (Section 3.3) and flash this:

```cpp
#include <Wire.h>
#include <MAX30105.h>      // SparkFun MAX3010x library
#include <MPU6050.h>        // Electronic Cats or Jeff Rowberg's library

MAX30105 particleSensor;
MPU6050 mpu;

const int GSR_PIN = 34;
unsigned long lastSample = 0;
const unsigned long SAMPLE_INTERVAL_MS = 15;  // ~64 Hz loop tick

void setup() {
  Serial.begin(115200);
  Wire.begin(21, 22);

  if (!particleSensor.begin(Wire, I2C_SPEED_FAST)) {
    Serial.println("MAX30102 not found — check wiring");
    while (1);
  }
  particleSensor.setup();  // default: red+IR LEDs, sample avg 4, 100Hz internal

  mpu.initialize();
  if (!mpu.testConnection()) {
    Serial.println("MPU6050 not found — check wiring");
    while (1);
  }

  pinMode(GSR_PIN, INPUT);

  Serial.println("timestamp_ms,ir,red,gsr_raw,acc_x,acc_y,acc_z");
}

void loop() {
  unsigned long now = millis();
  if (now - lastSample < SAMPLE_INTERVAL_MS) return;
  lastSample = now;

  long irValue  = particleSensor.getIR();
  long redValue = particleSensor.getRed();
  int  gsrRaw   = analogRead(GSR_PIN);

  int16_t ax, ay, az;
  mpu.getAcceleration(&ax, &ay, &az);

  Serial.print(now);         Serial.print(",");
  Serial.print(irValue);     Serial.print(",");
  Serial.print(redValue);    Serial.print(",");
  Serial.print(gsrRaw);      Serial.print(",");
  Serial.print(ax);          Serial.print(",");
  Serial.print(ay);          Serial.print(",");
  Serial.println(az);
}
```

**Design decision — single 64Hz loop instead of three separate timers:** BVP, EDA, and ACC all get sampled together on one ~15ms tick, rather than firing at their WESAD-native rates (64/4/32Hz) individually. This is simpler and has a smaller error surface for first bring-up. Downsampling EDA and ACC to their target rates happens in Python later — the same approach already documented for the WESAD→hardware sampling-rate mapping. Don't add multi-rate timer logic yet; get one clean rate working first.

**Expected serial monitor output** (115200 baud):
```
timestamp_ms,ir,red,gsr_raw,acc_x,acc_y,acc_z
14203,58420,12100,1820,412,-88,16344
14218,58433,12105,1818,410,-90,16340
14233,58390,12098,1825,415,-85,16351
...
```

- `ir`/`red` in the range 5,000–200,000 with a visible slow oscillation when a finger is on the sensor (no finger = flat near-zero or erratic noise)
- `gsr_raw` — a 12-bit ADC reading (0–4095), stable at rest, slow drift is normal
- `acc_x/y/z` — one axis should read close to ±16384 (1g) at rest depending on orientation, the other two near 0

---

## 6. Why TP4056/battery wiring is deferred

You have the TP4056 module, but **wire it later, not now.** Reasons:

- ESP32 dev boards regulate 5V (via VIN or USB) down to 3.3V onboard. A LiPo cell sits at 3.7–4.2V, which is under most onboard regulators' safe minimum input — feeding it directly into 5V/VIN risks brownouts or unreliable operation.
- Running on USB power during firmware bring-up removes one variable. If something doesn't work, you want to know it's not a power issue.
- Battery integration belongs in Phase 4 (portable/wearable form factor for the actual gameplay sessions) — there's no need for it during signal validation.

When you do wire it: `TP4056 OUT+` → ESP32 `5V`/`VIN`, `OUT-` → `GND`, LiPo cell → `BAT+`/`BAT-`, USB-micro → `IN+`/`IN-` for charging. Confirm cell polarity with a multimeter before connecting — reversed LiPo polarity is a fire risk, not just a "won't work" risk.

---

## 7. Troubleshooting — symptom → cause → fix

| Symptom | Likely cause | Fix |
|---|---|---|
| I2C scan finds nothing | GND not connected, or SDA/SCL swapped | Multimeter continuity check on every GND wire. Verify SDA→21, SCL→22 exactly (not swapped). |
| I2C scan finds only one device | Second device's power or GND wire loose | Reseat that module's VCC and GND individually — check each with multimeter, not just visually. |
| MAX30102 IR reading stays near 0 with finger on | LED not powering on — often a VIN issue | Confirm VIN is 3.3V, not left floating. Some breakouts need `particleSensor.setup()` called with explicit LED current args if default is too low — check your specific breakout's example sketch. |
| MAX30102 reading is very noisy / erratic | Finger pressure too light, or ambient light interference | Apply firm but not tight finger pressure; shield sensor from direct light. |
| GSR reading is always 0 or always 4095 (saturated) | Electrodes not contacting skin, or wired to 5V instead of 3.3V | Confirm electrode contact; re-verify VCC is 3V3, not 5V. |
| GSR reading is extremely noisy, jumping wildly | Loose electrode contact, or missing GND reference | Ensure electrodes are snug on two fingers of the same hand; check GND wire. |
| MPU6050 `testConnection()` fails | AD0 floating with no onboard pulldown, or address conflict | Wire AD0 directly to GND. Re-run the I2C scanner — confirm 0x68 appears. |
| Serial monitor shows garbage characters | Baud rate mismatch | Confirm both the sketch (`Serial.begin(115200)`) and Serial Monitor dropdown are set to 115200. |
| ESP32 resets/reboots randomly under load | Insufficient current from USB port | Try a different USB cable/port — some deliver too little current for ESP32 + 3 peripherals. A USB 3.0 port or powered hub often fixes this. |
| Upload fails / "Failed to connect to ESP32" | Board not in bootloader mode | Hold the BOOT button on the ESP32 while upload starts, release once "Connecting..." appears in the IDE console. |

---

## 8. Verification checklist (M2 milestone criteria)

Work through these in order — each depends on the previous one passing.

- [ ] I2C scanner shows both `0x57` (MAX30102) and `0x68` (MPU6050)
- [ ] BVP shows a visible periodic waveform with finger on sensor — plot the `ir` column in Python/Excel over a 10s window and look for pulse-like oscillation
- [ ] Resting heart rate estimate from BVP peaks falls in 50–100 BPM range
- [ ] GSR baseline is stable at rest — no oscillation or dropout over a 60s recording
- [ ] Tapping the table or typing on a keyboard produces a visible spike in `acc_x/y/z` — confirms MPU6050 motion detection works
- [ ] CSV serial output has no dropped/malformed rows over a 5-minute recording (check row count ≈ expected count at ~64Hz)

Once all six pass, M2 is closed and you're ready to run the existing Python pipeline (`preprocess.py`, `features.py`) directly on this hardware CSV, per Phase 3 of the workplan.

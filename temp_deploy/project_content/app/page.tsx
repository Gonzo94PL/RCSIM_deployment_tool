'use client';

import React, { useState, useEffect, useRef } from 'react';
import { 
  Battery, 
  Settings, 
  Cpu, 
  Sliders, 
  FileText, 
  AlertTriangle, 
  Zap, 
  Download,
  Bluetooth,
} from 'lucide-react';

// Import subcomponents
import { LiveMonitor } from '../components/LiveMonitor';
import { ProfileEditor } from '../components/ProfileEditor';
import { HardwareConfig } from '../components/HardwareConfig';
import { CoprocessorTab } from '../components/CoprocessorTab';
import { BluetoothConfig } from '../components/BluetoothConfig';
import { useTranslation } from '../hooks/useTranslation';


// Interfaces
interface ChannelMapping {
  name: string;
  device: string;
  axis: string;
  outputChannel: number;
  reverse: boolean;
  subTrim: number;
  epaMin: number;
  epaMax: number;
  expo: number;
  deadzone?: number;
  type?: 'bidirectional' | 'unidirectional' | 'split_axis';
}

interface Profile {
  id: string;
  name: string;
  batteryType: string;
  mappings: { [key: string]: ChannelMapping };
  gearboxConfig?: {
    mode: 'none' | 'sequential';
    num_forward_gears: number;
    reverse_throttle_limit: number;
    btn_up: string;
    btn_down: string;
  };
  driveModeBtn?: string;
  cruiseBtn?: string;
}

interface UsbController {
  id: string;
  name: string;
  connected: boolean;
  active: boolean;
}

export default function RCTerminalPage() {
  const { t, lang, setLang } = useTranslation();
  const [isConnected, setIsConnected] = useState(true);
  const [isArmed, setIsArmed] = useState(true);
  const [theme, setTheme] = useState<'dark' | 'light'>('dark');
  const [activeTab, setActiveTab] = useState<'monitor' | 'profile' | 'matrix' | 'hardware' | 'coprocessor' | 'bluetooth'>('monitor');
  const [channels, setChannels] = useState<number[]>(new Array(16).fill(1500));
  const [batteryVoltage, setBatteryVoltage] = useState(7.84);
  const [batteryPercent, setBatteryPercent] = useState(72);
  const [activeProfileId, setActiveProfileId] = useState('quad-5-cal');
  const [isLowBattery, setIsLowBattery] = useState(false);
  const [batteryDemoMode, setBatteryDemoMode] = useState(false);
  const [simulationActive] = useState(true);
  const [testSignalType, setTestSignalType] = useState<'sine' | 'saw' | 'noise' | 'center'>('center');
  const [noiseSpeed] = useState(1);
  const [virtualJoystickLeft, setVirtualJoystickLeft] = useState({ x: 0, y: 0 });
  const [virtualJoystickRight, setVirtualJoystickRight] = useState({ x: 0, y: 0 });
  const [currentGear, setCurrentGear] = useState<number>(1);
  const [driveMode, setDriveMode] = useState<string>('sport');
  const [cruiseActive, setCruiseActive] = useState<boolean>(false);
  const [cruiseThrottleUs, setCruiseThrottleUs] = useState<number>(1500);
  const [rssi, setRssi] = useState<number>(-65);
  const [linkQuality, setLinkQuality] = useState<number>(100);

  const [usbControllers, setUsbControllers] = useState<UsbController[]>([
    { id: 'usb-1', name: 'RadioMaster TX16S (USB HID)', connected: true, active: false },
    { id: 'usb-2', name: 'Sony DualSense Wireless Controller', connected: true, active: false },
    { id: 'usb-3', name: 'FrSky Taranis Q X7 USB Config', connected: false, active: false }
  ]);

  const [logs, setLogs] = useState<string[]>([
    "[SYSTEM] Inicjalizacja pętli głównej Raspberry Pi 5...",
    "[SYSTEM] Oczekiwanie na dane statusowe z backendu..."
  ]);

  const otaScrollRef = useRef<HTMLDivElement | null>(null);
  const uartScrollRef = useRef<HTMLDivElement | null>(null);
  const logsInitializedRef = useRef(false);

  const [profiles, setProfiles] = useState<Profile[]>([
    {
      id: 'quad-5-cal',
      name: 'Quad_5_Cal',
      batteryType: '2S',
      gearboxConfig: {
        mode: 'none',
        num_forward_gears: 3,
        reverse_throttle_limit: 0.3,
        btn_up: '',
        btn_down: '',
      },
      driveModeBtn: '',
      cruiseBtn: '',
      mappings: {
        'Throttle': { name: 'Throttle', device: 'usb-1', axis: 'Oś Z', outputChannel: 3, reverse: false, subTrim: 0, epaMin: 1000, epaMax: 2000, expo: 10 },
        'Aileron': { name: 'Aileron', device: 'usb-1', axis: 'Oś X', outputChannel: 1, reverse: false, subTrim: 5, epaMin: 1100, epaMax: 1900, expo: 35 },
        'Elevator': { name: 'Elevator', device: 'usb-1', axis: 'Oś Y', outputChannel: 2, reverse: true, subTrim: -2, epaMin: 1100, epaMax: 1900, expo: 35 },
        'Rudder': { name: 'Rudder', device: 'usb-1', axis: 'Oś Rz', outputChannel: 4, reverse: false, subTrim: 0, epaMin: 1050, epaMax: 1950, expo: 20 },
        'Aux1': { name: 'Aux1', device: 'usb-1', axis: 'Przełącznik SA', outputChannel: 5, reverse: false, subTrim: 0, epaMin: 1000, epaMax: 2000, expo: 0 },
        'Aux2': { name: 'Aux2', device: 'usb-1', axis: 'Przełącznik SB', outputChannel: 6, reverse: false, subTrim: 0, epaMin: 1000, epaMax: 2000, expo: 0 },
        'Aux3': { name: 'Aux3', device: 'None', axis: 'Brak', outputChannel: 7, reverse: false, subTrim: 0, epaMin: 1000, epaMax: 2000, expo: 0 },
        'Aux4': { name: 'Aux4', device: 'None', axis: 'Brak', outputChannel: 8, reverse: false, subTrim: 0, epaMin: 1000, epaMax: 2000, expo: 0 },
      }
    },
    {
      id: 'plane-zagi-fpv',
      name: 'Plane_Zagi_FPV',
      batteryType: '3S',
      gearboxConfig: {
        mode: 'none',
        num_forward_gears: 3,
        reverse_throttle_limit: 0.3,
        btn_up: '',
        btn_down: '',
      },
      driveModeBtn: '',
      cruiseBtn: '',
      mappings: {
        'Throttle': { name: 'Throttle', device: 'usb-1', axis: 'Oś Z', outputChannel: 3, reverse: false, subTrim: 0, epaMin: 1000, epaMax: 2000, expo: 5 },
        'Aileron': { name: 'Aileron', device: 'usb-1', axis: 'Oś X', outputChannel: 1, reverse: false, subTrim: 12, epaMin: 1150, epaMax: 1850, expo: 45 },
        'Elevator': { name: 'Elevator', device: 'usb-1', axis: 'Oś Y', outputChannel: 2, reverse: false, subTrim: -8, epaMin: 1150, epaMax: 1850, expo: 45 },
        'Rudder': { name: 'Rudder', device: 'None', axis: 'Brak', outputChannel: 4, reverse: false, subTrim: 0, epaMin: 1000, epaMax: 2000, expo: 0 },
        'Aux1': { name: 'Aux1', device: 'usb-2', axis: 'Przycisk L1', outputChannel: 5, reverse: false, subTrim: 0, epaMin: 1000, epaMax: 2000, expo: 0 },
        'Aux2': { name: 'Aux2', device: 'usb-2', axis: 'D-Pad góra', outputChannel: 6, reverse: false, subTrim: 0, epaMin: 1000, epaMax: 2000, expo: 0 },
        'Aux3': { name: 'Aux3', device: 'None', axis: 'Brak', outputChannel: 7, reverse: false, subTrim: 0, epaMin: 1000, epaMax: 2000, expo: 0 },
        'Aux4': { name: 'Aux4', device: 'None', axis: 'Brak', outputChannel: 8, reverse: false, subTrim: 0, epaMin: 1000, epaMax: 2000, expo: 0 },
      }
    }
  ]);

  const [profileFormOpen, setProfileFormOpen] = useState(false);
  const [newProfileName, setNewProfileName] = useState('');
  const [newProfileBattery, setNewProfileBattery] = useState('3S');
  const [editingMappingKey, setEditingMappingKey] = useState<string | null>(null);

  const [hardwareSettings, setHardwareSettings] = useState({
    protocol: 'SBUS',
    serialPort: '/dev/ttyACM0',
    upsI2C: '0x40',
    upsSensor: 'INA219'
  });

  const [otaState, setOtaState] = useState<'idle' | 'uploading' | 'waiting_reset' | 'verifying' | 'writing' | 'success' | 'error'>('idle');
  const [showResetModal, setShowResetModal] = useState(false);
  const [otaProgress, setOtaProgress] = useState(0);
  const [otaLogs, setOtaLogs] = useState<string[]>([]);
  const [selectedFirmwareFile, setSelectedFirmwareFile] = useState<string>('firmware.bin');
  const [firmwareTarget, setFirmwareTarget] = useState<'esp32' | 'stm32' | 'xiao_rp2350'>('xiao_rp2350');
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);

  const otaStateRef = useRef(otaState);
  useEffect(() => {
    otaStateRef.current = otaState;
  }, [otaState]);

  const currentProfile = profiles.find(p => p.id === activeProfileId) || profiles[0];

  const loadConfigFromBackend = async () => {
    try {
      const res = await fetch('/api/config');
      if (res.ok) {
        const config = await res.json();
        
        if (config.language && (config.language === 'pl' || config.language === 'en')) {
          setLang(config.language);
        }

        // 1. Ustawienia sprzętowe
        setHardwareSettings({
          protocol: (config.output_protocol || 'SBUS').toUpperCase(),
          serialPort: config.output_port || '/dev/ttyAMA0',
          upsI2C: config.ups_i2c || '0x42',
          upsSensor: config.ups_sensor || 'INA219'
        });

        if (config.selected_profile) {
          setActiveProfileId(config.selected_profile);
        }

        // 2. Profile i mapowania osi
        if (config.profiles) {
          const loadedProfiles: Profile[] = Object.keys(config.profiles).map(key => {
            const bp = config.profiles[key];
            const mappings: { [key: string]: ChannelMapping } = {
              'Throttle': { name: 'Throttle', device: 'None', axis: 'Brak', outputChannel: 3, reverse: false, subTrim: 0, epaMin: 1000, epaMax: 2000, expo: 10 },
              'Aileron': { name: 'Aileron', device: 'None', axis: 'Brak', outputChannel: 1, reverse: false, subTrim: 0, epaMin: 1100, epaMax: 1900, expo: 20 },
              'Elevator': { name: 'Elevator', device: 'None', axis: 'Brak', outputChannel: 2, reverse: false, subTrim: 0, epaMin: 1100, epaMax: 1900, expo: 20 },
              'Rudder': { name: 'Rudder', device: 'None', axis: 'Brak', outputChannel: 4, reverse: false, subTrim: 0, epaMin: 1100, epaMax: 1900, expo: 10 },
              'Aux1': { name: 'Aux1', device: 'None', axis: 'Brak', outputChannel: 5, reverse: false, subTrim: 0, epaMin: 1000, epaMax: 2000, expo: 0 },
              'Aux2': { name: 'Aux2', device: 'None', axis: 'Brak', outputChannel: 6, reverse: false, subTrim: 0, epaMin: 1000, epaMax: 2000, expo: 0 },
              'Aux3': { name: 'Aux3', device: 'None', axis: 'Brak', outputChannel: 7, reverse: false, subTrim: 0, epaMin: 1000, epaMax: 2000, expo: 0 },
              'Aux4': { name: 'Aux4', device: 'None', axis: 'Brak', outputChannel: 8, reverse: false, subTrim: 0, epaMin: 1000, epaMax: 2000, expo: 0 },
            };

            if (bp.inputs) {
              bp.inputs.forEach((input: any) => {
                const devName = input.device_name;
                if (input.mappings) {
                  input.mappings.forEach((m: any) => {
                    const name = m.name;
                    if (mappings[name]) {
                      mappings[name] = {
                        name: name,
                        device: devName,
                        axis: m.axis || 'Brak',
                        outputChannel: m.channel || mappings[name].outputChannel,
                        reverse: m.reverse || false,
                        subTrim: m.sub_trim || 0,
                        epaMin: m.min_limit || 1000,
                        epaMax: m.max_limit || 2000,
                        expo: m.expo || 0,
                        deadzone: m.deadzone || 20,
                        type: m.type || 'bidirectional'
                      };
                    }
                  });
                }
              });
            }

            return {
              id: key,
              name: bp.name || key,
              batteryType: bp.battery_type || '2S',
              mappings: mappings,
              gearboxConfig: {
                mode: (bp.gearbox_config?.mode || 'none') as 'none' | 'sequential',
                num_forward_gears: bp.gearbox_config?.num_forward_gears || 3,
                reverse_throttle_limit: bp.gearbox_config?.reverse_throttle_limit || 0.3,
                btn_up: bp.gearbox_config?.btn_up || '',
                btn_down: bp.gearbox_config?.btn_down || '',
              },
              driveModeBtn: bp.drive_mode_btn || '',
              cruiseBtn: bp.cruise_btn || '',
            };
          });

          if (loadedProfiles.length > 0) {
            setProfiles(loadedProfiles);
          }
        }
      }
    } catch (e) {
      console.error("Error loading backend config:", e);
    }
  };

  const saveConfigToBackend = async (
    updatedProfiles: Profile[],
    updatedHW = hardwareSettings,
    activeId = activeProfileId
  ) => {
    const backendProfiles: { [key: string]: any } = {};

    updatedProfiles.forEach(p => {
      const inputsMap: { [key: string]: any[] } = {};
      Object.keys(p.mappings).forEach(key => {
        const m = p.mappings[key];
        if (m.device && m.device !== 'None' && m.device !== 'Brak') {
          if (!inputsMap[m.device]) {
            inputsMap[m.device] = [];
          }
          inputsMap[m.device].push({
            name: m.name,
            axis: m.axis,
            channel: m.outputChannel,
            reverse: m.reverse,
            sub_trim: m.subTrim,
            min_limit: m.epaMin,
            max_limit: m.epaMax,
            expo: m.expo,
            deadzone: m.deadzone || 20,
            type: m.type || 'bidirectional'
          });
        }
      });

      const inputsList = Object.keys(inputsMap).map(devName => ({
        device_name: devName,
        mappings: inputsMap[devName]
      }));

      backendProfiles[p.id] = {
        name: p.name,
        battery_type: p.batteryType,
        inputs: inputsList,
        gearbox_config: p.gearboxConfig || {
          mode: 'none',
          num_forward_gears: 3,
          reverse_throttle_limit: 0.3,
          btn_up: '',
          btn_down: '',
        },
        drive_mode_btn: p.driveModeBtn || '',
        cruise_btn: p.cruiseBtn || '',
      };
    });

    const payload = {
      language: lang,
      api: {
        host: "0.0.0.0",
        port: 8080
      },
      output_protocol: updatedHW.protocol.toLowerCase(),
      output_port: updatedHW.serialPort,
      ups_sensor: updatedHW.upsSensor,
      ups_i2c: updatedHW.upsI2C,
      selected_profile: activeId,
      profiles: backendProfiles
    };

    try {
      const res = await fetch('/api/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (res.ok) {
        setLogs(prev => [...prev, `[SYSTEM] Konfiguracja zapisana pomyślnie na RPi.`]);
      } else {
        alert("Błąd zapisu konfiguracji na backendzie!");
      }
    } catch (e) {
      console.error("Error posting config:", e);
    }
  };

  useEffect(() => {
    loadConfigFromBackend();
    const localTheme = localStorage.getItem('rcsim_theme') as 'dark' | 'light' | null;
    if (localTheme && (localTheme === 'light' || localTheme === 'dark')) {
      setTheme(localTheme);
    }
  }, []);

  useEffect(() => {
    if (otaScrollRef.current) {
      otaScrollRef.current.scrollTop = otaScrollRef.current.scrollHeight;
    }
  }, [otaLogs]);

  useEffect(() => {
    if (uartScrollRef.current) {
      uartScrollRef.current.scrollTop = uartScrollRef.current.scrollHeight;
    }
  }, [logs]);

  // Poll real-time status and devices from the backend
  useEffect(() => {
    let statusInterval: NodeJS.Timeout;
    let devicesInterval: NodeJS.Timeout;
    let logsInterval: NodeJS.Timeout;

    const fetchStatus = async () => {
      try {
        const res = await fetch('/api/status');
        if (res.ok) {
          const data = await res.json();
          if (data.channels) {
            setChannels(data.channels);
          }
          if (data.battery) {
            setBatteryVoltage(data.battery.voltage);
            setBatteryPercent(data.battery.percentage);
            setBatteryDemoMode(!!data.battery.demo_mode);
            const activeMinSafe = currentProfile.batteryType === '2S' ? 6.6 : 
                                  currentProfile.batteryType === '3S' ? 9.9 :
                                  currentProfile.batteryType === '4S' ? 13.2 : 19.8;
            setIsLowBattery(data.battery.voltage < activeMinSafe);
          }
          if (data.paused !== undefined) {
            setIsArmed(!data.paused);
          }
          if (data.gear !== undefined) {
            setCurrentGear(data.gear);
          }
          if (data.drive_mode !== undefined) {
            setDriveMode(data.drive_mode);
          }
          if (data.cruise_active !== undefined) {
            setCruiseActive(data.cruise_active);
          }
          if (data.cruise_throttle_us !== undefined) {
            setCruiseThrottleUs(data.cruise_throttle_us);
          }
          if (data.rssi !== undefined) {
            setRssi(data.rssi);
          }
          if (data.link_quality !== undefined) {
            setLinkQuality(data.link_quality);
          }
          setIsConnected(true);

          if (!logsInitializedRef.current) {
            logsInitializedRef.current = true;
            const initialLogs = [
              "[SYSTEM] Inicjalizacja pętli głównej Raspberry Pi 5...",
              `[SYSTEM] Port szeregowy ${hardwareSettings.serialPort} otwarty pomyślnie.`,
            ];

            if (firmwareTarget === 'xiao_rp2350') {
              initialLogs.push(`[SYSTEM] Nawiązano połączenie z XIAO RP2350 (koprocesor) przez USB-C.`);
            } else if (firmwareTarget === 'stm32') {
              initialLogs.push(`[SYSTEM] Nawiązano połączenie z STM32 Blue Pill (koprocesor) przez UART.`);
            } else {
              initialLogs.push(`[SYSTEM] Nawiązano połączenie z ESP32 (koprocesor) przez piny UART.`);
            }

            if (data.battery && data.battery.demo_mode) {
              initialLogs.push(`[WARN] Moduł UPS (np. INA219) nie został wykryty na szynie I2C. Uruchomiono emulator zasilania.`);
            } else {
              initialLogs.push(`[INFO] Wykryto moduł UPS ${hardwareSettings.upsSensor} na adresie I2C: ${hardwareSettings.upsI2C}. Pomiar napięcia aktywny.`);
            }

            initialLogs.push(`[STATUS] Profil '${currentProfile.name}' załadowany pomyślnie ze szczegółami mapowania.`);

            setLogs(initialLogs);
          }
        } else {
          setIsConnected(false);
        }
      } catch (e) {
        setIsConnected(false);
      }
    };

    const fetchDevices = async () => {
      try {
        const res = await fetch('/api/devices');
        if (res.ok) {
          const data = await res.json();
          const mapped = data.map((d: any) => ({
            id: d.path,
            name: d.name,
            connected: true,
            active: false
          }));
          setUsbControllers(mapped);
        }
      } catch (e) {
        console.error("Error fetching devices:", e);
      }
    };

    const fetchCoprocessorLogs = async () => {
      if (otaStateRef.current !== 'idle') return;
      try {
        const res = await fetch('/api/firmware/logs');
        if (res.ok) {
          const data = await res.json();
          if (data.logs && data.logs.length > 0) {
            setOtaLogs(data.logs);
          }
        }
      } catch (e) {}
    };

    fetchStatus();
    fetchDevices();
    fetchCoprocessorLogs();

    statusInterval = setInterval(fetchStatus, 100);
    devicesInterval = setInterval(fetchDevices, 3000);
    logsInterval = setInterval(fetchCoprocessorLogs, 1000);

    return () => {
      clearInterval(statusInterval);
      clearInterval(devicesInterval);
      clearInterval(logsInterval);
    };
  }, [currentProfile.batteryType]);

  // Main simulation loop (only active when offline / not connected)
  useEffect(() => {
    let timer: NodeJS.Timeout;
    let tickCounter = 0;

    const runSimulation = () => {
      if (isConnected) {
        timer = setTimeout(runSimulation, 60);
        return;
      }
      tickCounter++;

      setBatteryVoltage(prev => {
        let maxV = 8.4;
        let minV = 6.4;
        if (currentProfile.batteryType === '3S') { maxV = 12.6; minV = 9.6; }
        if (currentProfile.batteryType === '4S') { maxV = 16.8; minV = 12.8; }
        if (currentProfile.batteryType === '6S') { maxV = 25.2; minV = 19.2; }

        let nextV = prev - 0.0002 + (Math.sin(tickCounter * 0.05) * 0.001);
        if (nextV > maxV) nextV = maxV;
        if (nextV < minV - 0.5) nextV = maxV;

        const pct = Math.round(Math.max(0, Math.min(100, ((nextV - minV) / (maxV - minV)) * 100)));
        setBatteryPercent(pct);

        const activeMinSafe = currentProfile.batteryType === '2S' ? 6.6 : 
                              currentProfile.batteryType === '3S' ? 9.9 :
                              currentProfile.batteryType === '4S' ? 13.2 : 19.8;
                              
        setIsLowBattery(nextV < activeMinSafe);
        return parseFloat(nextV.toFixed(2));
      });

      setChannels(prev => {
        const nextChannels = [...prev];
        const time = tickCounter * 0.1 * noiseSpeed;

        Object.keys(currentProfile.mappings).forEach((key) => {
          const mapping = currentProfile.mappings[key];
          if (!mapping || mapping.device === 'None') return;

          let rawInputValue = 0.0;

          if (testSignalType === 'sine') {
            const shift = key === 'Throttle' ? 0 : 
                          key === 'Aileron' ? 1 :
                          key === 'Elevator' ? 2 : 3;
            rawInputValue = Math.sin(time + shift);
          } else if (testSignalType === 'saw') {
            rawInputValue = ((tickCounter + (key === 'Throttle' ? 0 : 5)) % 40) / 20 - 1;
          } else if (testSignalType === 'noise') {
            rawInputValue = (Math.sin(time * 1.5) * 0.5) + (Math.cos(time * 0.7) * 0.5);
          } else {
            if (key === 'Throttle') rawInputValue = virtualJoystickLeft.y;
            else if (key === 'Rudder') rawInputValue = virtualJoystickLeft.x;
            else if (key === 'Aileron') rawInputValue = virtualJoystickRight.x;
            else if (key === 'Elevator') rawInputValue = virtualJoystickRight.y;
            else if (key.startsWith('Aux')) rawInputValue = Math.sin(time * 0.1) > 0 ? 1 : -1;
          }

          const expoDecimal = mapping.expo / 100;
          let calculatedValue = (1 - expoDecimal) * rawInputValue + expoDecimal * Math.pow(rawInputValue, 3);
          let usOffset = mapping.subTrim;
          let usValue = 1500 + (calculatedValue * 500);

          if (mapping.reverse) usValue = 3000 - usValue;
          usValue += usOffset;

          if (usValue < mapping.epaMin) usValue = mapping.epaMin;
          if (usValue > mapping.epaMax) usValue = mapping.epaMax;

          const outIndex = mapping.outputChannel - 1;
          if (outIndex >= 0 && outIndex < 16) {
            nextChannels[outIndex] = Math.round(usValue);
          }
        });

        if (tickCounter % 4 === 0) {
          setUsbControllers(prevControllers => 
            prevControllers.map(c => {
              if (c.connected) {
                const activeMappingsCount = Object.values(currentProfile.mappings)
                  .filter(m => m.device === c.id).length;
                return { ...c, active: activeMappingsCount > 0 && Math.random() > 0.2 };
              }
              return c;
            })
          );
        }

        return nextChannels;
      });

      if (simulationActive && tickCounter % 45 === 0) {
        setLogs(prev => {
          const nextLogs = [...prev];
          const seed = Math.random();
          let logStr = "";
          
          if (seed < 0.1) logStr = `[WARN] Suma kontrolna ramki RC [id=${Math.round(tickCounter * 4.3)}]. Pominięto.`;
          else if (seed < 0.3) logStr = `[INFO] Stabilny strumień danych: 16 kanałów [Protokół: ${hardwareSettings.protocol}].`;
          else if (seed < 0.5) logStr = `[INFO] Stan koprocesora: Temperatura ESP 38.4°C.`;
          else if (seed < 0.7) logStr = `[STATUS] UPS LiPo: Napięcie wynosi ${batteryVoltage}V (${batteryPercent}%).`;
          else logStr = `[INFO] Połączenie aktywne WebSocket (Klient UI ok).`;

          if (nextLogs.length > 30) nextLogs.shift();
          return [...nextLogs, logStr];
        });
      }

      if (simulationActive) {
        timer = setTimeout(runSimulation, 60);
      }
    };

    if (simulationActive) {
      timer = setTimeout(runSimulation, 60);
    }

    return () => clearTimeout(timer);
  }, [simulationActive, currentProfile, testSignalType, virtualJoystickLeft, virtualJoystickRight, batteryVoltage, batteryPercent, hardwareSettings.protocol]);

  const toggleConnection = () => {
    setIsConnected(!isConnected);
    setLogs(prev => [...prev, isConnected ? `[SYSTEM] Klient WebSocket odłączony.` : `[SYSTEM] Klient WebSocket ponownie podłączony.`]);
  };

  const toggleArm = async () => {
    const targetState = !isArmed;
    setIsArmed(targetState);
    setLogs(prev => [...prev, `[SYSTEM] Sygnał RC: ${targetState ? 'UZBROJONY' : 'ROZBROJONY'} (lokalnie).`]);
    if (isConnected) {
      try {
        const res = await fetch(`/api/status/arm?arm=${targetState}`, { method: 'POST' });
        if (res.ok) {
          const data = await res.json();
          setIsArmed(!data.paused);
          setLogs(prev => [...prev.slice(0, -1), `[SYSTEM] Sygnał RC: ${targetState ? 'UZBROJONY' : 'ROZBROJONY'}.`]);
        }
      } catch (e) {
        console.error("Error toggling arm:", e);
      }
    }
  };

  const handleCreateProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newProfileName.trim()) return;

    const id = newProfileName.toLowerCase().replace(/[^a-z0-9]/g, '-');
    if (profiles.some(p => p.id === id)) {
      alert("Profil o tej nazwie już istnieje!");
      return;
    }

    const defaultMappings: { [key: string]: ChannelMapping } = {
      'Throttle': { name: 'Throttle', device: 'None', axis: 'Brak', outputChannel: 3, reverse: false, subTrim: 0, epaMin: 1000, epaMax: 2000, expo: 10 },
      'Aileron': { name: 'Aileron', device: 'None', axis: 'Brak', outputChannel: 1, reverse: false, subTrim: 0, epaMin: 1100, epaMax: 1900, expo: 20 },
      'Elevator': { name: 'Elevator', device: 'None', axis: 'Brak', outputChannel: 2, reverse: false, subTrim: 0, epaMin: 1100, epaMax: 1900, expo: 20 },
      'Rudder': { name: 'Rudder', device: 'None', axis: 'Brak', outputChannel: 4, reverse: false, subTrim: 0, epaMin: 1100, epaMax: 1900, expo: 10 },
      'Aux1': { name: 'Aux1', device: 'None', axis: 'Brak', outputChannel: 5, reverse: false, subTrim: 0, epaMin: 1000, epaMax: 2000, expo: 0 },
      'Aux2': { name: 'Aux2', device: 'None', axis: 'Brak', outputChannel: 6, reverse: false, subTrim: 0, epaMin: 1000, epaMax: 2000, expo: 0 },
      'Aux3': { name: 'Aux3', device: 'None', axis: 'Brak', outputChannel: 7, reverse: false, subTrim: 0, epaMin: 1000, epaMax: 2000, expo: 0 },
      'Aux4': { name: 'Aux4', device: 'None', axis: 'Brak', outputChannel: 8, reverse: false, subTrim: 0, epaMin: 1000, epaMax: 2000, expo: 0 },
    };

    const newProfile: Profile = { id, name: newProfileName.trim(), batteryType: newProfileBattery, mappings: defaultMappings };
    const updated = [...profiles, newProfile];
    setProfiles(updated);
    setActiveProfileId(id);
    setNewProfileName('');
    setProfileFormOpen(false);
    await saveConfigToBackend(updated, hardwareSettings, id);
    setLogs(prev => [...prev, `[STATUS] Utworzono profil: **${newProfile.name}**.`]);
  };

  const handleCloneProfile = async () => {
    const original = currentProfile;
    const cloneId = `${original.id}-clone-${Date.now().toString().slice(-4)}`;
    const cloneName = `${original.name}_Kopia`;

    const clonedProfile: Profile = {
      ...original,
      id: cloneId,
      name: cloneName,
      mappings: JSON.parse(JSON.stringify(original.mappings))
    };

    const updated = [...profiles, clonedProfile];
    setProfiles(updated);
    setActiveProfileId(cloneId);
    await saveConfigToBackend(updated, hardwareSettings, cloneId);
    setLogs(prev => [...prev, `[STATUS] Sklonowano profil: **${cloneName}**.`]);
  };

  const handleDeleteProfile = async () => {
    if (profiles.length <= 1) {
      alert("Nie można usunąć jedynego profilu!");
      return;
    }

    const confirmResult = window.confirm(`Czy na pewno usunąć profil '${currentProfile.name}'?`);
    if (confirmResult) {
      const remaining = profiles.filter(p => p.id !== currentProfile.id);
      setProfiles(remaining);
      const nextId = remaining[0].id;
      setActiveProfileId(nextId);
      await saveConfigToBackend(remaining, hardwareSettings, nextId);
      setLogs(prev => [...prev, `[STATUS] Usunięto profil: **${currentProfile.name}**.`]);
    }
  };

  const handleUpdateMapping = async (key: string, updatedFields: Partial<ChannelMapping>) => {
    if (updatedFields.epaMin !== undefined && updatedFields.epaMax !== undefined && updatedFields.epaMin >= updatedFields.epaMax) return;
    if (updatedFields.epaMin !== undefined && updatedFields.epaMin >= currentProfile.mappings[key].epaMax) return;
    if (updatedFields.epaMax !== undefined && updatedFields.epaMax <= currentProfile.mappings[key].epaMin) return;

    const updatedProfiles = profiles.map(p => {
      if (p.id === currentProfile.id) {
        return {
          ...p,
          mappings: {
            ...p.mappings,
            [key]: { ...p.mappings[key], ...updatedFields }
          }
        };
      }
      return p;
    });

    setProfiles(updatedProfiles);
    await saveConfigToBackend(updatedProfiles, hardwareSettings, activeProfileId);
  };

  const handleUpdateGearboxConfig = async (updatedFields: Partial<NonNullable<Profile['gearboxConfig']>>) => {
    const updatedProfiles = profiles.map(p => {
      if (p.id === currentProfile.id) {
        return {
          ...p,
          gearboxConfig: {
            mode: (updatedFields.mode !== undefined ? updatedFields.mode : (p.gearboxConfig?.mode || 'none')) as 'none' | 'sequential',
            num_forward_gears: updatedFields.num_forward_gears !== undefined ? updatedFields.num_forward_gears : (p.gearboxConfig?.num_forward_gears || 3),
            reverse_throttle_limit: updatedFields.reverse_throttle_limit !== undefined ? updatedFields.reverse_throttle_limit : (p.gearboxConfig?.reverse_throttle_limit || 0.3),
            btn_up: updatedFields.btn_up !== undefined ? updatedFields.btn_up : (p.gearboxConfig?.btn_up || ''),
            btn_down: updatedFields.btn_down !== undefined ? updatedFields.btn_down : (p.gearboxConfig?.btn_down || ''),
          }
        };
      }
      return p;
    });

    setProfiles(updatedProfiles);
    await saveConfigToBackend(updatedProfiles, hardwareSettings, activeProfileId);
  };

  const handleUpdateProfileFields = async (updatedFields: Partial<Profile>) => {
    const updatedProfiles = profiles.map(p => {
      if (p.id === currentProfile.id) {
        return {
          ...p,
          ...updatedFields
        };
      }
      return p;
    });

    setProfiles(updatedProfiles);
    await saveConfigToBackend(updatedProfiles, hardwareSettings, activeProfileId);
  };

  const handleSaveHardware = async (e: React.FormEvent) => {
    e.preventDefault();
    const i2cRegex = /^0x[0-9a-fA-F]{2}$/;
    if (!i2cRegex.test(hardwareSettings.upsI2C)) {
      alert("Błąd walidacji: Adres I2C musi być poprawną wartością szesnastkową w formacie np. 0x40");
      return;
    }

    await saveConfigToBackend(profiles, hardwareSettings, activeProfileId);
        setLogs(prev => [...prev, `[SYSTEM] Zapisano ustawienia sprzętowe.`]);
    alert("Ustawienia sprzętowe zostały pomyślnie zastosowane!");
  };

  // Przechowuje resolve() Promisa z etapu oczekiwania na RESET
  const resetResolveRef = React.useRef<((confirmed: boolean) => void) | null>(null);

  const handleCompileOta = async () => {
    if (otaState !== 'idle' && otaState !== 'success' && otaState !== 'error') return;

    setOtaState('writing');
    setOtaProgress(20);
    setOtaLogs([
      `⚙️ Rozpoczęto kompilację kodu dla ${firmwareTarget === 'xiao_rp2350' ? 'XIAO RP2350' : 'STM32'} (PlatformIO)...`,
      "⏳ Może to zająć dłuższą chwilę w przypadku pierwszego uruchomienia...",
      "🛠️ Trwa kompilacja oprogramowania w tle..."
    ]);

    try {
      const response = await fetch(`/api/firmware/compile?target=${encodeURIComponent(firmwareTarget)}`, {
        method: 'POST',
      });
      const result = await response.json();
      if (response.ok && result.status === 'success') {
        setOtaProgress(100);
        setOtaState('success');
        setOtaLogs(prev => [
          ...prev,
          `✅ Kompilacja kodu ${firmwareTarget === 'xiao_rp2350' ? 'RP2350' : 'STM32'} zakończona sukcesem!`,
          "🔬 Log kompilacji:",
          result.log || "",
          firmwareTarget === 'xiao_rp2350'
            ? "🎉 Wygenerowany plik .uf2 jest gotowy do wgrania na XIAO RP2350 przez picotool."
            : "🎉 Wygenerowany plik firmware.bin jest gotowy do wgrania na płytkę."
        ]);
        setLogs(prev => [...prev, `[SYSTEM] Kompilacja ${firmwareTarget === 'xiao_rp2350' ? 'RP2350' : 'STM32'} zakończona sukcesem.`]);
      } else {
        setOtaProgress(100);
        setOtaState('error');
        setOtaLogs(prev => [
          ...prev,
          "❌ Błąd kompilacji kodu!",
          result.message || "Błąd.",
          "🔬 Log kompilacji:",
          result.log || result.detail || ""
        ]);
        setLogs(prev => [...prev, `[ERROR] Błąd kompilacji ${firmwareTarget === 'xiao_rp2350' ? 'RP2350' : 'STM32'}.`]);
      }
    } catch (error: any) {
      setOtaProgress(100);
      setOtaState('error');
      setOtaLogs(prev => [
        ...prev,
        `❌ Wyjątek sieciowy / API: ${error.message || error}`
      ]);
      setLogs(prev => [...prev, `[ERROR] Wyjątek podczas kompilacji.`]);
    }
  };

  const handleTriggerOta = async () => {
    if (otaState !== 'idle' && otaState !== 'success' && otaState !== 'error') return;

    // --- Obsługa STM32 / XIAO RP2350 ---
    if (firmwareTarget === 'stm32' || firmwareTarget === 'xiao_rp2350') {
      const targetLabel = firmwareTarget === 'xiao_rp2350' ? 'XIAO RP2350' : 'STM32';
      setOtaState('writing');
      setOtaProgress(30);
      setOtaLogs([
        `⚙️ Rozpoczęto przygotowanie do programowania ${targetLabel}...`,
        firmwareTarget === 'xiao_rp2350'
          ? "⏳ Przygotowywanie wgrywania przez USB (picotool)..."
          : "⏳ Wstrzymywanie nadawania sygnału RC...",
        firmwareTarget === 'xiao_rp2350'
          ? "🔌 Nawiązywanie połączenia USB z XIAO RP2350 (tryb BOOTSEL)..."
          : "🔌 Nawiązywanie połączenia przez OpenOCD..."
      ]);

      try {
        const formData = new FormData();
        if (uploadedFile) {
          formData.append('file', uploadedFile);
        }

        const response = await fetch(`/api/firmware/flash?port=${encodeURIComponent(hardwareSettings.serialPort)}&filename=${encodeURIComponent(selectedFirmwareFile)}&target=${firmwareTarget}`, {
          method: 'POST',
          body: formData
        });

        const result = await response.json();
        if (response.ok && result.status === 'success') {
          setOtaProgress(100);
          setOtaState('success');
          setOtaLogs(prev => [
            ...prev,
            `✅ Programowanie ${targetLabel} pomyślne!`,
            firmwareTarget === 'xiao_rp2350' ? "🔬 Log picotool:" : "🔬 Log OpenOCD:",
            result.log || "",
            "🎉 System zresetowany i gotowy do pracy.",
            "💚 Transmisja RC została automatycznie wznowiona."
          ]);
          setLogs(prev => [...prev, `[SYSTEM] ${targetLabel} zaktualizowany pomyślnie.`]);
        } else {
          setOtaProgress(100);
          setOtaState('error');
          setOtaLogs(prev => [
            ...prev,
            `❌ Błąd wgrywania oprogramowania do ${targetLabel}!`,
            result.message || "Nieznany błąd.",
            firmwareTarget === 'xiao_rp2350' ? "🔬 Szczegóły błędu (picotool log):" : "🔬 Szczegóły błędu (OpenOCD log):",
            result.log || result.detail || ""
          ]);
          setLogs(prev => [...prev, `[ERROR] Błąd aktualizacji ${targetLabel}.`]);
        }
      } catch (error: any) {
        setOtaProgress(100);
        setOtaState('error');
        setOtaLogs(prev => [
          ...prev,
          `❌ Wyjątek sieciowy / API: ${error.message || error}`
        ]);
        setLogs(prev => [...prev, `[ERROR] Wyjątek podczas programowania ${targetLabel}.`]);
      }
      return;
    }

    // --- Obsługa ESP32 ---
    setOtaState('uploading');
    setOtaProgress(10);
    setOtaLogs([
      "🔋 Rozpoczęto przygotowanie do wgrywania oprogramowania...",
      "⏳ Wstrzymywanie nadawania sygnału RC i blokowanie portu szeregowego...",
      "🔌 Ściąganie pinu GPIO 24 (ESP32 GPIO 0) do stanu niskiego..."
    ]);

    try {
      // 1. Wywołujemy endpoint prepare
      const prepResponse = await fetch('/api/firmware/prepare', { method: 'POST' });
      if (!prepResponse.ok) {
        throw new Error("Nie udało się przygotować koprocesora (Błąd API /prepare)");
      }

      setOtaProgress(30);
      setOtaState('waiting_reset');
      setOtaLogs(prev => [
        ...prev,
        "📌 Gotowe! Pin GPIO 0 na ESP32 został ustawiony w stan LOW.",
        "👉 KROK 2/3: Wciśnij teraz krótko przycisk RESET na plecach płytki ESP32-CAM.",
        "💬 Poczekaj na otwarcie modalu i potwierdź naciśnięcie przycisku..."
      ]);

      // Pokazujemy wbudowany modal React (zamiast window.confirm)
      setShowResetModal(true);
      const confirmed: boolean = await new Promise<boolean>((resolve) => {
        resetResolveRef.current = resolve;
      });
      setShowResetModal(false);

      if (!confirmed) {
        setOtaLogs(prev => [...prev, "❌ Operacja anulowana przez użytkownika. Przywracanie normalnej pracy..."]);
        await fetch('/api/firmware/resume', { method: 'POST' });
        setOtaState('idle');
        setOtaProgress(0);
        setLogs(prev => [...prev, `[SYSTEM] Flashowanie anulowane. Wznowiono transmisję RC.`]);
        return;
      }

      setOtaLogs(prev => [
        ...prev,
        "✅ Potwierdzono naciśnięcie RESET. ESP32 jest teraz w trybie bootloadera.",
        "⚡ KROK 3/3: Rozpoczynanie procesu wgrywania pamięci flash (esptool)..."
      ]);
      setOtaProgress(50);
      setOtaState('writing');

      // 2. Uruchamiamy właściwe flashowanie
      const formData = new FormData();
      if (uploadedFile) {
        formData.append('file', uploadedFile);
      }

      const response = await fetch(`/api/firmware/flash?port=${encodeURIComponent(hardwareSettings.serialPort)}&filename=${encodeURIComponent(selectedFirmwareFile)}&target=esp32`, {
        method: 'POST',
        body: formData
      });
      
      const result = await response.json();
      if (response.ok && result.status === 'success') {
        setOtaProgress(100);
        setOtaState('success');
        setOtaLogs(prev => [
          ...prev, 
          "✅ esptool: Zapis pamięci flash zakończony sukcesem!",
          "🔬 Log esptool:",
          result.log || "",
          "🎉 Wgrywanie pomyślne! Resetowanie koprocesora ESP32...",
          "👉 KROK KOŃCOWY: Wciśnij ponownie przycisk RESET na ESP32-CAM (bez zworki!), aby uruchomić normalną pracę.",
          "💚 Transmisja RC została wznowiona."
        ]);
        setLogs(prev => [...prev, `[SYSTEM] ESP32 zaktualizowany pomyślnie.`]);
      } else {
        setOtaProgress(100);
        setOtaState('error');
        setOtaLogs(prev => [
          ...prev, 
          "❌ Błąd wgrywania oprogramowania!",
          result.message || "Nieznany błąd.",
          "🔬 Szczegóły błędu (esptool log):",
          result.log || result.detail || ""
        ]);
        setLogs(prev => [...prev, `[ERROR] Błąd aktualizacji ESP32.`]);
      }
    } catch (error: any) {
      setOtaProgress(100);
      setOtaState('error');
      setShowResetModal(false);
      if (resetResolveRef.current) { resetResolveRef.current(false); resetResolveRef.current = null; }
      setOtaLogs(prev => [
        ...prev, 
        `❌ Wyjątek sieciowy / API: ${error.message || error}`
      ]);
      setLogs(prev => [...prev, `[ERROR] Wyjątek podczas programowania ESP32.`]);
    }
  };

  const handleResetConfirmed = () => {
    setOtaLogs(prev => [...prev, "🖱️ [GUI] Użytkownik potwierdził: przycisk RESET naciśnięty ✔"]);
    if (resetResolveRef.current) { resetResolveRef.current(true); resetResolveRef.current = null; }
  };

  const handleResetCancel = () => {
    if (resetResolveRef.current) { resetResolveRef.current(false); resetResolveRef.current = null; }
  };

  const handleClearOtaState = () => {
    setOtaState('idle');
    setOtaLogs([]);
  };

  const handleVirtualJoystickDrag = (
    e: React.MouseEvent<HTMLDivElement> | React.TouchEvent<HTMLDivElement>, 
    stick: 'left' | 'right'
  ) => {
    e.preventDefault();
    const container = e.currentTarget;
    const rect = container.getBoundingClientRect();
    const centerX = rect.left + rect.width / 2;
    const centerY = rect.top + rect.height / 2;

    const clientX = 'touches' in e ? e.touches[0].clientX : e.clientX;
    const clientY = 'touches' in e ? e.touches[0].clientY : e.clientY;

    let dx = (clientX - centerX) / (rect.width / 2);
    let dy = -(clientY - centerY) / (rect.height / 2);

    const magnitude = Math.sqrt(dx * dx + dy * dy);
    if (magnitude > 1) {
      dx /= magnitude;
      dy /= magnitude;
    }

    if (stick === 'left') {
      setVirtualJoystickLeft({ x: parseFloat(dx.toFixed(2)), y: parseFloat(dy.toFixed(2)) });
    } else {
      setVirtualJoystickRight({ x: parseFloat(dx.toFixed(2)), y: parseFloat(dy.toFixed(2)) });
    }
  };

  const handleVirtualJoystickRelease = (stick: 'left' | 'right') => {
    if (stick === 'left') {
      setVirtualJoystickLeft(prev => ({ x: 0, y: prev.y }));
    } else {
      setVirtualJoystickRight({ x: 0, y: 0 });
    }
  };

  const handleExportOfflineUI = () => {
    const htmlString = `<!DOCTYPE html>
<html lang="pl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>RC Terminal - Tryb Polowy Offline</title>
</head>
<body class="p-4">
    <div class="max-w-4xl mx-auto">
        <h1>🎛️ Terminal RC (Lokalny Static)</h1>
    </div>
</body>
</html>`;

    const blob = new Blob([htmlString], { type: 'text/html' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `static_ui_rpi_field.html`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
    
    setLogs(prev => [...prev, "[SYSTEM] Wyeksportowano uproszczoną paczkę HTML."]);
  };

  return (
    <main className={`min-h-screen bg-[#020617] text-slate-100 antialiased font-sans select-none ${theme === 'light' ? 'light-theme' : ''}`} id="rc-root-container">
      {/* HEADER */}
      <header 
        id="rc-terminal-header"
        className={`sticky top-0 z-30 bg-slate-950/80 backdrop-blur-md border-b border-slate-900 shadow-lg transition-colors duration-350 ${
          isLowBattery ? "bg-red-950/60 border-red-900/50 animate-pulse" : ""
        }`}
      >
        <div className="max-w-7xl mx-auto px-6 py-4 flex flex-col sm:flex-row justify-between items-center gap-4">
          <div className="flex items-center gap-3 w-full sm:w-auto justify-between sm:justify-start">
            <div>
              <div className="flex items-center gap-2">
                <span className="p-1 px-2 bg-indigo-600 text-white font-black text-xs rounded tracking-wider uppercase shadow-md shadow-indigo-500/20">RPi 5</span>
                <h1 className="text-xl font-black tracking-tight text-white flex items-center gap-2">
                  {t('app_title')}
                </h1>
              </div>
              <div className="flex items-center gap-2 mt-1">
                <span className="h-2 w-2 rounded-full bg-indigo-500 animate-ping"></span>
                <p className="text-xs text-slate-400">
                  Model: <strong className="font-semibold text-white">{currentProfile.name}</strong> 
                  <span className="text-slate-500 font-normal ml-1">({currentProfile.batteryType} LiPo)</span>
                </p>
              </div>
            </div>

            <select
              id="header-profile-dropdown"
              value={activeProfileId}
              onChange={(e) => {
                setActiveProfileId(e.target.value);
                setLogs(prev => [...prev, `[STATUS] Przełączono profil: **${profiles.find(p => p.id === e.target.value)?.name}**.`]);
              }}
              className="sm:hidden p-2 text-xs bg-slate-900 border border-slate-800 rounded font-semibold text-white focus:outline-none"
            >
              {profiles.map(p => (
                <option key={p.id} value={p.id}>{p.name}</option>
              ))}
            </select>
          </div>

          <div className="flex items-center gap-3 w-full sm:w-auto justify-end">
            {/* Theme Toggle */}
            <button
              id="header-theme-toggle"
              onClick={() => {
                const newTheme = theme === 'dark' ? 'light' : 'dark';
                setTheme(newTheme);
                localStorage.setItem('rcsim_theme', newTheme);
              }}
              className="h-11 w-11 flex items-center justify-center bg-slate-900 border border-slate-805 hover:border-slate-700 rounded-xl text-sm focus:outline-none cursor-pointer transition shadow-xl"
              title={theme === 'dark' ? "Tryb Jasny" : "Tryb Ciemny"}
            >
              {theme === 'dark' ? '☀️' : '🌙'}
            </button>

            {/* Language Selector */}
            <select
              id="header-language-select"
              value={lang}
              onChange={(e) => {
                const newLang = e.target.value as any;
                setLang(newLang);
                saveConfigToBackend(profiles, hardwareSettings, activeProfileId);
              }}
              className="h-11 px-3 bg-slate-900 border border-slate-805 hover:border-slate-700 rounded-xl text-xs font-bold text-slate-300 focus:outline-none cursor-pointer transition shadow-xl"
            >
              <option value="pl">PL</option>
              <option value="en">EN</option>
            </select>

            <div 
              id="header-battery-indicator"
              className={`flex items-center gap-3 h-11 px-4 rounded-xl border font-mono text-sm shadow-xl transition-all ${
                isLowBattery 
                  ? "bg-red-950/40 text-red-400 border-red-900" 
                  : "bg-emerald-950/20 text-emerald-400 border-emerald-900/50"
              }`}
            >
              <Battery className={`h-4.5 w-4.5 ${isLowBattery ? "animate-bounce text-red-500" : ""}`} />
              <div>
                <div className="text-[10px] uppercase font-sans tracking-wide text-slate-500 font-bold flex items-center gap-1">
                  {t('battery_level')}
                  {batteryDemoMode && <span className="px-1 py-0.2 bg-amber-500/20 text-amber-400 border border-amber-500/30 rounded text-[8px] font-black uppercase">Demo</span>}
                </div>
                <div className="text-sm font-black mt-0.5">
                  {batteryVoltage.toFixed(2)}V <span className="text-xs font-normal">({batteryPercent}%)</span>
                </div>
              </div>
            </div>

            {/* VIRTUAL GEARBOX INDICATOR */}
            {currentProfile.gearboxConfig && currentProfile.gearboxConfig.mode !== 'none' && (
              <div 
                id="header-gear-indicator"
                className="flex items-center gap-3 h-11 px-4 rounded-xl border border-slate-805 bg-slate-900 text-xs font-bold shadow-xl"
              >
                <div className="text-left">
                  <div className="text-[9px] uppercase tracking-wide text-slate-500">{t('gearbox_current_gear')}</div>
                  <div className="text-xs font-black mt-0.5 text-indigo-400">
                    {currentGear === -1 ? 'R' : currentGear === 0 ? 'N' : currentGear}
                  </div>
                </div>
              </div>
            )}

            {/* RSSI & LQ TELEMETRY */}
            {isConnected && (
              <div 
                id="header-telemetry-indicator"
                className="flex items-center gap-3 h-11 px-4 rounded-xl border border-slate-805 bg-slate-900 text-xs font-bold shadow-xl"
              >
                <div className="text-left flex gap-3">
                  <div>
                    <div className="text-[9px] uppercase tracking-wide text-slate-500">{t('rssi_label')}</div>
                    <div className="text-xs font-black mt-0.5 text-emerald-400">
                      {rssi} dBm
                    </div>
                  </div>
                  <div className="border-l border-slate-800 pl-3">
                    <div className="text-[9px] uppercase tracking-wide text-slate-500">{t('lq_label')}</div>
                    <div className="text-xs font-black mt-0.5 text-emerald-400">
                      {linkQuality}%
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* ARM / DISARM BUTTON */}
            <button
              id="header-arm-toggle"
              onClick={toggleArm}
              className={`flex items-center gap-3 h-11 px-4 rounded-xl border text-xs font-bold cursor-pointer transition-all ${
                isArmed 
                  ? "bg-red-950/20 text-red-500 border-red-900/50 hover:bg-red-950/30" 
                  : "bg-slate-900 border-slate-800 hover:border-slate-700 text-slate-400 hover:text-white"
              }`}
            >
              <span className="relative flex h-2.5 w-2.5">
                {isArmed && <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>}
                <span className={`relative inline-flex rounded-full h-2.5 w-2.5 ${isArmed ? "bg-red-500" : "bg-slate-600"}`}></span>
              </span>
              <div className="text-left">
                <div className="text-[9px] uppercase tracking-wide text-slate-500">Sygnał RC</div>
                <div className="text-xs font-black mt-0.5">{isArmed ? t('status_armed') : t('btn_disarm')}</div>
              </div>
            </button>

            <button
              id="header-connection-toggle"
              onClick={toggleConnection}
              className={`flex items-center gap-3 h-11 px-4 rounded-xl border text-xs font-bold cursor-pointer transition-all ${
                isConnected 
                  ? "bg-emerald-950/20 text-emerald-400 border-emerald-900/50 hover:bg-emerald-950/30" 
                  : "bg-red-950/20 text-red-400 border-red-900 hover:bg-red-950/30"
              }`}
            >
              <span className={`h-2 w-2 rounded-full ${isConnected ? "bg-emerald-500 animate-pulse" : "bg-red-500"}`}></span>
              <div className="text-left">
                <div className="text-[9px] uppercase tracking-wide text-slate-500">Status WebSocket</div>
                <div className="text-xs font-black mt-0.5">{isConnected ? t('status_connected') : t('status_disconnected')}</div>
              </div>
            </button>
          </div>
        </div>
      </header>

      {/* MAIN CONTENT */}
      <div className="max-w-7xl mx-auto px-6 py-8" id="rc-main-workspace grid">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
          {/* NAVIGATION */}
          <nav className="col-span-12 lg:col-span-3 space-y-3" id="rc-tab-navigation">
            <p className="text-[10px] font-black text-slate-500 tracking-wider uppercase pl-2">{t('lang_en') === 'English' ? 'Configuration Modules' : 'Moduły Konfiguracji'}</p>
            <div className="grid grid-cols-1 sm:grid-cols-4 lg:grid-cols-1 gap-2">
              <button
                id="tab-btn-monitor"
                onClick={() => setActiveTab('monitor')}
                className={`flex items-center gap-3 p-3.5 rounded-xl text-left text-sm font-bold transition-all border ${
                  activeTab === 'monitor' 
                    ? "bg-indigo-600 text-white border-indigo-500 shadow-lg shadow-indigo-500/20" 
                    : "bg-slate-900/60 text-slate-400 border-slate-800/80 hover:bg-slate-900 hover:text-white"
                }`}
              >
                <Sliders className="h-4.5 w-4.5" />
                <span className="truncate">{t('tab_monitor')}</span>
              </button>

              <button
                id="tab-btn-profile"
                onClick={() => setActiveTab('profile')}
                className={`flex items-center gap-3 p-3.5 rounded-xl text-left text-sm font-bold transition-all border ${
                  activeTab === 'profile' 
                    ? "bg-indigo-600 text-white border-indigo-500 shadow-lg shadow-indigo-500/20" 
                    : "bg-slate-900/60 text-slate-400 border-slate-800/80 hover:bg-slate-900 hover:text-white"
                }`}
              >
                <FileText className="h-4.5 w-4.5" />
                <span className="truncate">{t('tab_profile')}</span>
              </button>

              <button
                id="tab-btn-hardware"
                onClick={() => setActiveTab('hardware')}
                className={`flex items-center gap-3 p-3.5 rounded-xl text-left text-sm font-bold transition-all border ${
                  activeTab === 'hardware' 
                    ? "bg-indigo-600 text-white border-indigo-500 shadow-lg shadow-indigo-500/20" 
                    : "bg-slate-900/60 text-slate-400 border-slate-800/80 hover:bg-slate-900 hover:text-white"
                }`}
              >
                <Settings className="h-4.5 w-4.5" />
                <span className="truncate">{t('tab_hardware')}</span>
              </button>

              <button
                id="tab-btn-coprocessor"
                onClick={() => setActiveTab('coprocessor')}
                className={`flex items-center gap-3 p-3.5 rounded-xl text-left text-sm font-bold transition-all border ${
                  activeTab === 'coprocessor' 
                    ? "bg-indigo-600 text-white border-indigo-500 shadow-lg shadow-indigo-500/20" 
                    : "bg-slate-900/60 text-slate-400 border-slate-800/80 hover:bg-slate-900 hover:text-white"
                }`}
              >
                <Cpu className="h-4.5 w-4.5" />
                <span className="truncate">{t('tab_coprocessor')}</span>
              </button>

              <button
                id="tab-btn-bluetooth"
                onClick={() => setActiveTab('bluetooth')}
                className={`flex items-center gap-3 p-3.5 rounded-xl text-left text-sm font-bold transition-all border ${
                  activeTab === 'bluetooth' 
                    ? "bg-indigo-600 text-white border-indigo-500 shadow-lg shadow-indigo-500/20" 
                    : "bg-slate-900/60 text-slate-400 border-slate-800/80 hover:bg-slate-900 hover:text-white"
                }`}
              >
                <Bluetooth className="h-4.5 w-4.5" />
                <span className="truncate">{t('tab_bluetooth')}</span>
              </button>

            </div>

          </nav>

          {/* CONTENT ZONE */}
          <div className="col-span-12 lg:col-span-9" id="rc-tab-content-container">
            {activeTab === 'monitor' && (
              <LiveMonitor
                channels={channels}
                currentProfile={currentProfile}
                testSignalType={testSignalType}
                setTestSignalType={setTestSignalType}
                usbControllers={usbControllers}
                setUsbControllers={setUsbControllers}
                setLogs={setLogs}
                virtualJoystickLeft={virtualJoystickLeft}
                virtualJoystickRight={virtualJoystickRight}
                handleVirtualJoystickDrag={handleVirtualJoystickDrag}
                handleVirtualJoystickRelease={handleVirtualJoystickRelease}
                handleExportOfflineUI={handleExportOfflineUI}
                t={t}
                driveMode={driveMode}
                cruiseActive={cruiseActive}
                cruiseThrottleUs={cruiseThrottleUs}
              />
            )}

            {activeTab === 'profile' && (
              <ProfileEditor
                profiles={profiles}
                currentProfile={currentProfile}
                activeProfileId={activeProfileId}
                setActiveProfileId={setActiveProfileId}
                usbControllers={usbControllers}
                editingMappingKey={editingMappingKey}
                setEditingMappingKey={setEditingMappingKey}
                handleCreateProfile={handleCreateProfile}
                handleCloneProfile={handleCloneProfile}
                handleDeleteProfile={handleDeleteProfile}
                handleUpdateMapping={handleUpdateMapping}
                handleUpdateGearboxConfig={handleUpdateGearboxConfig}
                handleUpdateProfileFields={handleUpdateProfileFields}
                profileFormOpen={profileFormOpen}
                setProfileFormOpen={setProfileFormOpen}
                newProfileName={newProfileName}
                setNewProfileName={setNewProfileName}
                newProfileBattery={newProfileBattery}
                setNewProfileBattery={setNewProfileBattery}
                setLogs={setLogs}
                t={t}
              />
            )}

            {activeTab === 'hardware' && (
              <HardwareConfig
                hardwareSettings={hardwareSettings}
                setHardwareSettings={setHardwareSettings}
                handleSaveHardware={handleSaveHardware}
                t={t}
              />
            )}

            {activeTab === 'coprocessor' && (
              <CoprocessorTab
                otaState={otaState}
                otaProgress={otaProgress}
                otaLogs={otaLogs}
                selectedFirmwareFile={selectedFirmwareFile}
                setSelectedFirmwareFile={setSelectedFirmwareFile}
                firmwareTarget={firmwareTarget}
                setFirmwareTarget={setFirmwareTarget}
                uploadedFile={uploadedFile}
                setUploadedFile={setUploadedFile}
                handleTriggerOta={handleTriggerOta}
                handleCompileOta={handleCompileOta}
                logs={logs}
                otaScrollRef={otaScrollRef}
                uartScrollRef={uartScrollRef}
                showResetModal={showResetModal}
                onResetConfirmed={handleResetConfirmed}
                onResetCancel={handleResetCancel}
                t={t}
                clearOtaState={handleClearOtaState}
              />
            )}

            {activeTab === 'bluetooth' && (
              <BluetoothConfig t={t} setLogs={setLogs} />
            )}
          </div>
        </div>
      </div>
    </main>
  );
}

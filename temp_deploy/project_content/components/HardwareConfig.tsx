'use client';

import React from 'react';
import { Settings } from 'lucide-react';
import { TranslationFunction } from '../hooks/useTranslation';

interface HardwareSettings {
  protocol: string;
  serialPort: string;
  upsI2C: string;
  upsSensor: string;
}

interface HardwareConfigProps {
  hardwareSettings: HardwareSettings;
  setHardwareSettings: React.Dispatch<React.SetStateAction<HardwareSettings>>;
  handleSaveHardware: (e: React.FormEvent) => void;
  t: TranslationFunction;
}

export const HardwareConfig: React.FC<HardwareConfigProps> = ({
  hardwareSettings,
  setHardwareSettings,
  handleSaveHardware,
  t,
}) => {
  return (
    <div id="view-hardware" className="space-y-6">
      <form
        onSubmit={handleSaveHardware}
        className="bg-slate-900/40 backdrop-blur-md p-6 rounded-2xl border border-slate-800 shadow-xl space-y-6"
        id="hardware-settings-form"
      >
        <div>
          <h2 className="text-lg font-black text-white flex items-center gap-2">
            <Settings className="h-5 w-5 text-indigo-400" />
            {t('hardware_settings_title')}
          </h2>
          <p className="text-xs text-slate-400 mt-0.5">
            {t('hardware_settings_desc')}
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 text-xs text-slate-300">
          {/* Output settings */}
          <div className="space-y-4">
            <h3 className="text-[10px] font-bold text-slate-500 uppercase tracking-wider pl-1">{t('rc_output_header')}</h3>

            <div>
              <label className="block text-[10px] font-bold uppercase text-slate-400 mb-1">{t('protocol_label')}</label>
              <select
                id="hw-protocol-select"
                value={hardwareSettings.protocol}
                onChange={(e) => setHardwareSettings({ ...hardwareSettings, protocol: e.target.value })}
                className="w-full p-2.5 bg-slate-900 border border-slate-800 rounded-lg font-semibold text-white focus:outline-none focus:ring-1 focus:ring-indigo-500"
              >
                <option value="NOMAD">{t('protocol_nomad')}</option>
                <option value="CRSF">{t('protocol_crsf')}</option>
                <option value="SBUS">{t('protocol_sbus')}</option>
                <option value="IBUS">{t('protocol_ibus')}</option>
                <option value="PPM">{t('protocol_ppm')}</option>
              </select>
            </div>

            <div>
              <label className="block text-[10px] font-bold uppercase text-slate-400 mb-1">{t('serial_port_label')}</label>
              <select
                id="hw-serialport-select"
                value={hardwareSettings.serialPort}
                onChange={(e) => setHardwareSettings({ ...hardwareSettings, serialPort: e.target.value })}
                className="w-full p-2.5 bg-slate-900 border border-slate-800 rounded-lg text-white font-mono focus:outline-none"
              >
                <option value="/dev/ttyACM0">{t('serial_acm0')}</option>
                <option value="/dev/ttyACM1">/dev/ttyACM1</option>
                <option value="/dev/ttyACM2">/dev/ttyACM2</option>
                <option value="/dev/ttyACM3">/dev/ttyACM3</option>
                <option value="/dev/ttyACM4">/dev/ttyACM4</option>
                <option value="/dev/ttyACM5">/dev/ttyACM5</option>
                <option value="/dev/ttyAMA0">{t('serial_ama0')}</option>
                <option value="/dev/ttyUSB0">{t('serial_usb0')}</option>
                <option value="/dev/ttyS0">{t('serial_s0')}</option>
              </select>
            </div>
          </div>

          {/* Power / UPS monitor */}
          <div className="space-y-4">
            <h3 className="text-[10px] font-bold text-slate-500 uppercase tracking-wider pl-1">{t('power_telemetry_header')}</h3>

            <div>
              <label className="block text-[10px] font-bold uppercase text-slate-400 mb-1">{t('ups_sensor_label')}</label>
              <select
                id="hw-upssensor-select"
                value={hardwareSettings.upsSensor}
                onChange={(e) => setHardwareSettings({ ...hardwareSettings, upsSensor: e.target.value })}
                className="w-full p-2.5 bg-slate-900 border border-slate-800 rounded-lg text-white focus:outline-none"
              >
                <option value="INA219">{t('ups_default')}</option>
                <option value="ADS1115">{t('ups_ads')}</option>
                <option value="None">{t('ups_none')}</option>
              </select>
            </div>

            <div>
              <label className="block text-[10px] font-bold uppercase text-slate-400 mb-1">{t('i2c_address_label')}</label>
              <input
                id="hw-upsi2c-input"
                type="text"
                placeholder="np. 0x40"
                value={hardwareSettings.upsI2C}
                onChange={(e) => setHardwareSettings({ ...hardwareSettings, upsI2C: e.target.value })}
                className="w-full p-2.5 bg-slate-900 border border-slate-800 rounded-lg text-white font-mono focus:outline-none focus:ring-1 focus:ring-indigo-500"
                disabled={hardwareSettings.upsSensor === 'None'}
              />
            </div>
          </div>
        </div>

        <div className="flex justify-end pt-4 border-t border-slate-800/80">
          <button
            id="save-hardware-settings-btn"
            type="submit"
            className="w-full sm:w-auto p-2.5 px-6 bg-indigo-600 hover:bg-indigo-700 text-white font-bold text-xs rounded-xl shadow-lg active:scale-95 transition"
          >
            {t('apply_hardware_settings')}
          </button>
        </div>
      </form>
    </div>
  );
};

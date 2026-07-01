'use client';

import React, { useState, useEffect } from 'react';
import { Sliders, Zap, Download } from 'lucide-react';
import { TranslationFunction } from '../hooks/useTranslation';

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
}

interface Profile {
  id: string;
  name: string;
  batteryType: string;
  mappings: { [key: string]: ChannelMapping };
}

interface UsbController {
  id: string;
  name: string;
  connected: boolean;
  active: boolean;
}

interface LiveMonitorProps {
  channels: number[];
  currentProfile: Profile;
  testSignalType: 'sine' | 'saw' | 'noise' | 'center';
  setTestSignalType: (val: 'sine' | 'saw' | 'noise' | 'center') => void;
  usbControllers: UsbController[];
  setUsbControllers: React.Dispatch<React.SetStateAction<UsbController[]>>;
  setLogs: React.Dispatch<React.SetStateAction<string[]>>;
  virtualJoystickLeft: { x: number; y: number };
  virtualJoystickRight: { x: number; y: number };
  handleVirtualJoystickDrag: (
    e: React.MouseEvent<HTMLDivElement> | React.TouchEvent<HTMLDivElement>,
    stick: 'left' | 'right'
  ) => void;
  handleVirtualJoystickRelease: (stick: 'left' | 'right') => void;
  handleExportOfflineUI: () => void;
  t: TranslationFunction;
  driveMode: string;
  cruiseActive: boolean;
  cruiseThrottleUs: number;
}

export const LiveMonitor: React.FC<LiveMonitorProps> = ({
  channels,
  currentProfile,
  testSignalType,
  setTestSignalType,
  usbControllers,
  setUsbControllers,
  setLogs,
  virtualJoystickLeft,
  virtualJoystickRight,
  handleVirtualJoystickDrag,
  handleVirtualJoystickRelease,
  handleExportOfflineUI,
  t,
  driveMode,
  cruiseActive,
  cruiseThrottleUs,
}) => {
  const [selectedDiagPath, setSelectedDiagPath] = useState<string | null>(null);
  const [deviceState, setDeviceState] = useState<{
    axes: { code: number; name: string; value: number; min: number; max: number }[];
    buttons: number[];
  } | null>(null);

  // Set default diagnostics path to first connected device on load or when selected is no longer connected/valid
  useEffect(() => {
    const activeDev = usbControllers.find(u => u.connected);
    const selectedIsConnected = usbControllers.some(u => u.connected && u.id === selectedDiagPath);
    if (activeDev && (!selectedDiagPath || !selectedIsConnected)) {
      Promise.resolve().then(() => {
        setSelectedDiagPath(activeDev.id);
      });
    }
  }, [usbControllers, selectedDiagPath]);

  // Poll controller diagnostics from backend (10 Hz)
  useEffect(() => {
    if (!selectedDiagPath || !selectedDiagPath.startsWith('/')) {
      Promise.resolve().then(() => {
        setDeviceState(null);
      });
      return;
    }

    let intervalId: NodeJS.Timeout;

    const fetchDeviceState = async () => {
      try {
        const res = await fetch(`/api/devices/state?path=${encodeURIComponent(selectedDiagPath)}`);
        if (res.ok) {
          const data = await res.json();
          setDeviceState(data);
        }
      } catch (e) {
        console.error("Error fetching controller state:", e);
      }
    };

    fetchDeviceState();
    intervalId = setInterval(fetchDeviceState, 100);

    return () => clearInterval(intervalId);
  }, [selectedDiagPath]);

  return (
    <div id="view-monitor" className="space-y-6">
      {/* 16 Horizontal Progress Bars */}
      <div className="bg-slate-900/40 backdrop-blur-md p-6 rounded-2xl border border-slate-800 shadow-xl">
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 mb-6">
          <div>
            <h2 className="text-lg font-black text-white tracking-tight flex items-center gap-2">
              <span className="h-2 w-2 rounded-full bg-indigo-500 animate-pulse"></span>
              {t('live_channels_title')}
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              {t('live_channels_desc')}
            </p>
          </div>

          <div className="flex items-center gap-2 bg-slate-800/80 p-1.5 rounded-xl border border-slate-700">
            <span className="text-[10px] font-bold text-slate-400 uppercase px-2">{t('signal_source_title')}:</span>
            <select
              id="test-signal-select"
              value={testSignalType}
              onChange={(e) => setTestSignalType(e.target.value as any)}
              className="text-xs p-1.5 rounded bg-slate-900 text-white border border-slate-700 font-semibold focus:outline-none focus:ring-1 focus:ring-indigo-500"
            >
              <option value="center">{t('signal_center')}</option>
              <option value="sine">{t('signal_sine')}</option>
              <option value="saw">{t('signal_saw')}</option>
              <option value="noise">{t('signal_noise')}</option>
            </select>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4" id="channel-bars-grid">
          {channels.map((val, idx) => {
            const pct = Math.max(0, Math.min(100, ((val - 1000) / 1000) * 100));
            const isMapped = Object.values(currentProfile.mappings).some(
              (m) => m.outputChannel === idx + 1 && m.device !== 'None'
            );

            return (
              <div
                key={idx}
                id={`channel-bar-item-${idx + 1}`}
                className={`p-3.5 rounded-xl border transition-all duration-200 ${
                  isMapped
                    ? 'bg-indigo-950/20 border-indigo-500/30 shadow-md shadow-indigo-500/5'
                    : 'bg-slate-950/20 border-slate-800'
                }`}
              >
                <div className="flex justify-between items-center text-xs font-mono mb-1.5">
                  <span className="flex items-center gap-1.5 text-slate-400">
                    <span className={`h-1.5 w-1.5 rounded-full ${isMapped ? 'bg-indigo-500' : 'bg-slate-700'}`}></span>
                    CH {String(idx + 1).padStart(2, '0')}
                  </span>
                  <span className={`font-bold ${isMapped ? 'text-indigo-400' : 'text-slate-500'}`}>{val} us</span>
                </div>

                <div className="relative w-full h-3.5 bg-slate-950 rounded-full overflow-hidden border border-slate-800">
                  <div className="absolute left-1/2 top-0 bottom-0 w-0.5 bg-slate-800 z-10"></div>
                  <div
                    className={`h-full transition-all duration-75 rounded-full ${
                      isMapped
                        ? 'bg-gradient-to-r from-indigo-600 to-cyan-500 shadow-[0_0_8px_rgba(79,70,229,0.5)]'
                        : 'bg-slate-700'
                    }`}
                    style={{ width: `${pct}%` }}
                  ></div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* DRIVE MODE & CRUISE CONTROL CONTROLS */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Drive Mode Card */}
        <div className="bg-slate-900/40 backdrop-blur-md p-6 rounded-2xl border border-slate-800 shadow-xl space-y-4">
          <div className="flex items-center gap-2.5">
            <Sliders className="h-5 w-5 text-indigo-400" />
            <h3 className="text-sm font-black text-white uppercase tracking-wider">{t('drive_mode_label')}</h3>
          </div>
          <p className="text-xs text-slate-400 leading-relaxed font-sans">
            {t('is_english') === 'true' ? 'Switch vehicle dynamics and traction control profile.' : 'Przełącz profil dynamiki i kontroli trakcji pojazdu.'}
          </p>
          <div className="grid grid-cols-2 gap-2 text-xs font-bold">
            {(['sport', 'eco', 'crawler', 'wet'] as const).map((mode) => {
              const isActive = driveMode === mode;
              return (
                <button
                  key={mode}
                  id={`drive-mode-btn-${mode}`}
                  onClick={async () => {
                    try {
                      await fetch(`/api/status/drive_mode?mode=${mode}`, { method: 'POST' });
                      setLogs((prev) => [...prev, `[SYSTEM] Tryb jazdy zmieniony na: ${mode.toUpperCase()}`]);
                    } catch (e) {
                      console.error(e);
                    }
                  }}
                  className={`p-3 rounded-xl border text-center transition-all cursor-pointer ${
                    isActive
                      ? 'bg-indigo-600 border-indigo-500 text-white shadow-lg'
                      : 'bg-slate-950/40 border-slate-800 text-slate-400 hover:text-white hover:bg-slate-900'
                  }`}
                >
                  {t(`drive_mode_${mode}`)}
                </button>
              );
            })}
          </div>
        </div>

        {/* Cruise Control Card */}
        <div className="bg-slate-900/40 backdrop-blur-md p-6 rounded-2xl border border-slate-800 shadow-xl space-y-4">
          <div className="flex items-center gap-2.5">
            <Zap className="h-5 w-5 text-indigo-400" />
            <h3 className="text-sm font-black text-white uppercase tracking-wider">{t('cruise_control_label')}</h3>
          </div>
          <p className="text-xs text-slate-400 leading-relaxed font-sans">
            {t('is_english') === 'true' ? 'Lock current throttle value or adjust speed automatically.' : 'Zablokuj aktualny poziom gazu lub dostosuj automatyczną prędkość.'}
          </p>

          <div className="flex items-center justify-between p-3 bg-slate-950/40 border border-slate-850 rounded-xl">
            <div>
              <span className="text-[10px] text-slate-500 block uppercase font-bold">{t('cruise_speed')}</span>
              <span className="text-sm font-black text-indigo-400 font-mono">{cruiseThrottleUs} us</span>
            </div>

            <button
              id="live-cruise-toggle"
              onClick={async () => {
                const targetState = !cruiseActive;
                try {
                  await fetch(`/api/status/cruise?active=${targetState}&throttle_us=1650`, { method: 'POST' });
                  setLogs((prev) => [...prev, `[SYSTEM] Tempomat: ${targetState ? 'WŁĄCZONY (1650 us)' : 'WYŁĄCZONY'}`]);
                } catch (e) {
                  console.error(e);
                }
              }}
              className={`p-2 px-4 rounded-lg font-bold text-xs border cursor-pointer transition-all ${
                cruiseActive
                  ? 'bg-emerald-600 border-emerald-500 text-white shadow-md'
                  : 'bg-slate-900 border-slate-800 text-slate-400 hover:text-white hover:bg-slate-800'
              }`}
            >
              {cruiseActive ? (t('is_english') === 'true' ? 'Active' : 'Aktywny') : (t('is_english') === 'true' ? 'Enable' : 'Włącz')}
            </button>
          </div>
        </div>
      </div>

      {/* USB HID Controllers List */}
      <div className="bg-slate-900/40 backdrop-blur-md p-6 rounded-2xl border border-slate-800 shadow-xl font-sans">
        <div className="flex items-center gap-2 mb-4">
          <Sliders className="h-5 w-5 text-indigo-400" />
          <h3 className="text-sm font-black text-white uppercase tracking-wider">{t('usb_devices_title')}</h3>
        </div>
        <p className="text-xs text-slate-400 mb-4 leading-relaxed">
          {t('usb_devices_desc')}
        </p>

        <div className="grid grid-cols-1 gap-3" id="usb-hid-controllers-list">
          {usbControllers.length === 0 ? (
            <p className="text-xs text-slate-500 italic">{t('none')}</p>
          ) : (
            usbControllers.map((ctrl) => {
              const isSelected = selectedDiagPath === ctrl.id;
              return (
                <div
                  key={ctrl.id}
                  id={`usb-controller-${ctrl.id}`}
                  onClick={() => setSelectedDiagPath(ctrl.id)}
                  className={`flex flex-col sm:flex-row items-start sm:items-center justify-between p-4 rounded-xl border transition-all duration-200 cursor-pointer ${
                    isSelected
                      ? 'bg-indigo-950/30 border-indigo-500 shadow-lg'
                      : 'bg-slate-950/40 border-slate-800 hover:border-slate-700'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <span
                      className={`p-2 rounded-lg ${
                        isSelected ? 'bg-indigo-600 text-white' : 'bg-slate-800 text-slate-400'
                      }`}
                    >
                      <Sliders className="h-4 w-4" />
                    </span>
                    <div>
                      <p className="text-xs font-bold text-white">{ctrl.name}</p>
                      <p className="text-[10px] text-slate-500 font-mono mt-0.5">
                        {t('col_axis')}: {ctrl.id} • {isSelected ? t('status_active') : t('edit')}
                      </p>
                    </div>
                  </div>

                  <span className="text-[9px] font-black uppercase text-indigo-400 bg-indigo-950 border border-indigo-900/50 px-2 py-0.5 rounded mt-2 sm:mt-0">
                    {isSelected ? t('status_active') : t('edit')}
                  </span>
                </div>
              );
            })
          )}
        </div>

        {/* Real-time diagnostics of physical axes and buttons */}
        {selectedDiagPath && deviceState && (
          <div className="mt-6 p-5 bg-slate-950/65 rounded-xl border border-slate-800 space-y-6" id="controller-live-diagnostics">
            <h4 className="text-xs font-bold text-white flex items-center gap-2 uppercase tracking-wide">
              <span className="h-2 w-2 bg-indigo-500 rounded-full animate-ping"></span>
              {t('controller_diag_title')} (Matrix)
            </h4>

            {/* Axes */}
            <div className="space-y-3">
              <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block">{t('col_axis')}</span>
              {deviceState.axes.length === 0 ? (
                <p className="text-xs text-slate-500 italic">{t('none')}</p>
              ) : (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  {deviceState.axes.map((axis) => {
                    const range = axis.max - axis.min || 1;
                    const pct = Math.max(0, Math.min(100, ((axis.value - axis.min) / range) * 100));
                    return (
                      <div key={axis.code} className="p-3 bg-slate-900/60 rounded-xl border border-slate-850">
                        <div className="flex justify-between items-center text-[10px] font-mono mb-1 text-slate-400">
                          <span className="font-bold">{axis.name} (Kod {axis.code})</span>
                          <span className="text-indigo-400 font-bold">{axis.value}</span>
                        </div>
                        <div className="w-full bg-slate-950 h-2 rounded-full overflow-hidden border border-slate-800">
                          <div
                            className="bg-indigo-500 h-full rounded-full transition-all duration-75"
                            style={{ width: `${pct}%` }}
                          ></div>
                        </div>
                        <div className="flex justify-between text-[8px] text-slate-600 mt-1 font-mono">
                          <span>Min: {axis.min}</span>
                          <span>Max: {axis.max}</span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>

            {/* Buttons grid */}
            <div className="space-y-3">
              <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block">{t('buttons_label')} / Buttons</span>
              <div className="grid grid-cols-8 sm:grid-cols-16 gap-2">
                {Array.from({ length: 32 }).map((_, i) => {
                  // Standard key codes start around 288-319 for gamepads
                  const code = 288 + i; 
                  const isPressed = deviceState.buttons.includes(code);
                  return (
                    <div
                      key={code}
                      title={`Przycisk ${i} (Kod ${code})`}
                      className={`h-7 rounded-lg flex items-center justify-center font-mono text-[9px] font-bold border transition-all ${
                        isPressed
                          ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500 shadow-md shadow-emerald-500/5 font-black scale-105'
                          : 'bg-slate-900 border-slate-800 text-slate-600'
                      }`}
                    >
                      {i}
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        )}

        {/* Virtual Sticks */}
        <div className="mt-6 p-5 bg-slate-950/50 rounded-xl border border-dashed border-slate-800" id="virtual-sticks-container">
          <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wide mb-1 flex items-center gap-1.5">
            <Zap className="h-3.5 w-3.5 text-indigo-400" />
            {t('virtual_joystick_title')}
          </h4>
          <p className="text-[11px] text-slate-500 mb-6">
            {t('virtual_joystick_desc')}
          </p>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-8 justify-center">
            {/* Left Stick (Throttle / Yaw) */}
            <div className="flex flex-col items-center">
              <span className="text-[10px] font-bold text-slate-400 mb-3 uppercase tracking-wider">
                {t('joystick_left')}
              </span>
              <div
                className="relative w-36 h-36 bg-slate-900 border border-slate-800 rounded-full shadow-2xl flex items-center justify-center cursor-crosshair touch-none"
                onMouseMove={(e) => handleVirtualJoystickDrag(e, 'left')}
                onTouchMove={(e) => handleVirtualJoystickDrag(e, 'left')}
                onMouseLeave={() => handleVirtualJoystickRelease('left')}
                onTouchEnd={() => handleVirtualJoystickRelease('left')}
              >
                <div className="absolute w-full h-[1px] bg-slate-800"></div>
                <div className="absolute h-full w-[1px] bg-slate-800"></div>
                <div
                  className="absolute w-8 h-8 bg-gradient-to-br from-indigo-500 to-indigo-600 rounded-full shadow-lg flex items-center justify-center pointer-events-none transition-all duration-75"
                  style={{
                    transform: `translate(${virtualJoystickLeft.x * 55}px, ${-virtualJoystickLeft.y * 55}px)`,
                  }}
                >
                  <span className="h-2 w-2 bg-white rounded-full"></span>
                </div>
              </div>
              <div className="text-[10px] font-mono mt-3 text-slate-500 bg-slate-900/60 px-2 py-0.5 rounded border border-slate-800">
                Throttle: {Math.round((virtualJoystickLeft.y + 1) * 50)}% • Rudder: {Math.round((virtualJoystickLeft.x + 1) * 50)}%
              </div>
            </div>

            {/* Right Stick (Pitch / Roll) */}
            <div className="flex flex-col items-center">
              <span className="text-[10px] font-bold text-slate-400 mb-3 uppercase tracking-wider">
                {t('joystick_right')}
              </span>
              <div
                className="relative w-36 h-36 bg-slate-900 border border-slate-800 rounded-full shadow-2xl flex items-center justify-center cursor-crosshair touch-none"
                onMouseMove={(e) => handleVirtualJoystickDrag(e, 'right')}
                onTouchMove={(e) => handleVirtualJoystickDrag(e, 'right')}
                onMouseLeave={() => handleVirtualJoystickRelease('right')}
                onTouchEnd={() => handleVirtualJoystickRelease('right')}
              >
                <div className="absolute w-full h-[1px] bg-slate-800"></div>
                <div className="absolute h-full w-[1px] bg-slate-800"></div>
                <div
                  className="absolute w-8 h-8 bg-gradient-to-br from-indigo-500 to-indigo-600 rounded-full shadow-lg flex items-center justify-center pointer-events-none transition-all duration-75"
                  style={{
                    transform: `translate(${virtualJoystickRight.x * 55}px, ${-virtualJoystickRight.y * 55}px)`,
                  }}
                >
                  <span className="h-2 w-2 bg-white rounded-full"></span>
                </div>
              </div>
              <div className="text-[10px] font-mono mt-3 text-slate-500 bg-slate-900/60 px-2 py-0.5 rounded border border-slate-800">
                Pitch: {Math.round((virtualJoystickRight.y + 1) * 50)}% • Roll: {Math.round((virtualJoystickRight.x + 1) * 50)}%
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

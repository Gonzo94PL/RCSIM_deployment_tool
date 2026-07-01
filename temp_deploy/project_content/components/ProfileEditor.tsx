'use client';

import React, { useState } from 'react';
import { Sliders, FileText, Plus, Copy, Trash2, ChevronRight, Zap, Target } from 'lucide-react';
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
  deadzone?: number;
  type?: 'bidirectional' | 'unidirectional' | 'split_axis';
  deviceBrake?: string;
  axisBrake?: string;
  reverseBrake?: boolean;
  subTrimBrake?: number;
  expoBrake?: number;
  failsafeMode?: 'hold' | 'center' | 'custom';
  failsafeValue?: number;
  rawMin?: number | null;
  rawMax?: number | null;
  rawCenter?: number | null;
  rawMinBrake?: number | null;
  rawMaxBrake?: number | null;
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
  armBtn?: string;
  ffbAutocenter?: { [deviceName: string]: number };
  steeringRange?: { [deviceName: string]: number };
  hardwareRange?: { [deviceName: string]: number };
}

interface UsbController {
  id: string;
  name: string;
  connected: boolean;
  active: boolean;
}

interface ProfileEditorProps {
  profiles: Profile[];
  currentProfile: Profile;
  activeProfileId: string;
  setActiveProfileId: (id: string) => void;
  usbControllers: UsbController[];
  editingMappingKey: string | null;
  setEditingMappingKey: (key: string | null) => void;
  handleCreateProfile: (e: React.FormEvent) => void;
  handleCloneProfile: () => void;
  handleDeleteProfile: () => void;
  handleUpdateMapping: (key: string, updatedFields: Partial<ChannelMapping>) => void;
  handleUpdateGearboxConfig: (updatedFields: Partial<NonNullable<Profile['gearboxConfig']>>) => Promise<void>;
  handleUpdateProfileFields: (updatedFields: Partial<Profile>) => Promise<void>;
  profileFormOpen: boolean;
  setProfileFormOpen: (open: boolean) => void;
  newProfileName: string;
  setNewProfileName: (name: string) => void;
  newProfileBattery: string;
  setNewProfileBattery: (battery: string) => void;
  setLogs: React.Dispatch<React.SetStateAction<string[]>>;
  t: TranslationFunction;
}

export const ProfileEditor: React.FC<ProfileEditorProps> = ({
  profiles,
  currentProfile,
  activeProfileId,
  setActiveProfileId,
  usbControllers,
  editingMappingKey,
  setEditingMappingKey,
  handleCreateProfile,
  handleCloneProfile,
  handleDeleteProfile,
  handleUpdateMapping,
  handleUpdateGearboxConfig,
  handleUpdateProfileFields,
  profileFormOpen,
  setProfileFormOpen,
  newProfileName,
  setNewProfileName,
  newProfileBattery,
  setNewProfileBattery,
  setLogs,
  t,
}) => {
  const [subTab, setSubTab] = useState<'mixers' | 'definitions' | 'deadzones' | 'gearbox'>('mixers');
  const [isDetecting, setIsDetecting] = useState<string | null>(null);
  const [detectStatus, setDetectStatus] = useState<string>('');
  const [calibInfo, setCalibInfo] = useState<{
    subKey: string;
    devicePath: string;
    axisName: string;
  } | null>(null);
  const [liveRawVal, setLiveRawVal] = useState<number | null>(null);

  React.useEffect(() => {
    if (!calibInfo) {
      setLiveRawVal(null);
      return;
    }

    let active = true;
    const poll = async () => {
      try {
        const res = await fetch(`/api/devices/state?path=${encodeURIComponent(calibInfo.devicePath)}`);
        if (res.ok && active) {
          const data = await res.json();
          if (data && data.axes) {
            const axisData = data.axes.find((a: any) => a.name === calibInfo.axisName);
            if (axisData !== undefined) {
              setLiveRawVal(axisData.value);
            }
          }
        }
      } catch (e) {
        console.error("Error polling calibration values:", e);
      }
    };

    poll();
    const interval = setInterval(poll, 100);
    return () => {
      active = false;
      clearInterval(interval);
    };
  }, [calibInfo]);

  const startCalibration = (subKey: string, deviceName: string, axisName: string) => {
    const matched = usbControllers.find(u => u.id === deviceName || u.name === deviceName);
    if (!matched) {
      alert(t('calib_err_not_found') || 'Urządzenie nie jest podłączone lub nie zostało znalezione');
      return;
    }
    setCalibInfo({
      subKey,
      devicePath: matched.id,
      axisName
    });
  };

  const stopCalibration = () => {
    setCalibInfo(null);
  };

  const recordCalibPoint = (subKey: string, type: 'min' | 'max' | 'center') => {
    if (liveRawVal === null) return;
    const isGas = subKey.endsWith('_gas');
    const isBrake = subKey.endsWith('_brake');
    const mappingKey = isGas ? subKey.slice(0, -4) : isBrake ? subKey.slice(0, -6) : subKey;
    
    if (type === 'min') {
      if (isGas || !subKey.includes('_')) {
        handleUpdateMapping(mappingKey, { rawMin: liveRawVal });
      } else {
        handleUpdateMapping(mappingKey, { rawMinBrake: liveRawVal } as any);
      }
    } else if (type === 'max') {
      if (isGas || !subKey.includes('_')) {
        handleUpdateMapping(mappingKey, { rawMax: liveRawVal });
      } else {
        handleUpdateMapping(mappingKey, { rawMaxBrake: liveRawVal } as any);
      }
    } else if (type === 'center') {
      if (isGas || !subKey.includes('_')) {
        handleUpdateMapping(mappingKey, { rawCenter: liveRawVal });
      }
    }
  };

  const renderCalibrationUI = (subKey: string, mappingKey: string, item: ChannelMapping, deviceVal: string, axisVal: string) => {
    if (deviceVal === 'None' || axisVal === 'Brak') return null;

    const isGas = subKey.endsWith('_gas');
    const isBrake = subKey.endsWith('_brake');
    
    // Odczyt aktualnych wartości kalibracji
    const minVal = isGas ? item.rawMin : isBrake ? (item as any).rawMinBrake : item.rawMin;
    const maxVal = isGas ? item.rawMax : isBrake ? (item as any).rawMaxBrake : item.rawMax;
    const centerVal = isGas ? item.rawCenter : isBrake ? null : item.rawCenter;
    
    // Sprawdzenie czy aktywna jest kalibracja dla tego subKey
    const isCalibrating = calibInfo?.subKey === subKey;
    const hasAnyCalib = (minVal !== undefined && minVal !== null) || (maxVal !== undefined && maxVal !== null);

    return (
      <div className="mt-4 p-3 bg-slate-900/60 border border-slate-850 rounded-lg space-y-3 col-span-2">
        <div className="flex justify-between items-center">
          <span className="text-[10px] font-bold uppercase text-indigo-400">
            {t('calib_title') || 'Kalibracja Osi Fizycznej'}
          </span>
          {isCalibrating && (
            <span className="flex h-2 w-2 relative">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-red-500"></span>
            </span>
          )}
        </div>
        
        <p className="text-[9px] text-slate-500 leading-tight">
          {t('calib_desc') || 'Skonfiguruj krańcowe punkty fizyczne oraz punkt środkowy (neutralny) osi.'}
        </p>
        
        <div className="grid grid-cols-3 gap-2 text-[10px]">
          <div>
            <span className="block text-slate-500 mb-1">Min (Raw):</span>
            <input
              type="number"
              placeholder="Domyślne"
              value={minVal ?? ''}
              onChange={(e) => {
                const val = e.target.value === '' ? null : parseInt(e.target.value);
                if (isGas || (!isGas && !isBrake)) {
                  handleUpdateMapping(mappingKey, { rawMin: val });
                } else {
                  handleUpdateMapping(mappingKey, { rawMinBrake: val } as any);
                }
              }}
              className="w-full p-1.5 bg-slate-950 border border-slate-800 rounded text-white font-mono text-center text-xs focus:outline-none focus:ring-1 focus:ring-indigo-500"
            />
          </div>
          
          {(!isBrake) ? (
            <div>
              <span className="block text-slate-500 mb-1">Środek (Raw):</span>
              <input
                type="number"
                placeholder="Domyślne"
                value={centerVal ?? ''}
                onChange={(e) => {
                  const val = e.target.value === '' ? null : parseInt(e.target.value);
                  handleUpdateMapping(mappingKey, { rawCenter: val });
                }}
                className="w-full p-1.5 bg-slate-950 border border-slate-800 rounded text-white font-mono text-center text-xs focus:outline-none focus:ring-1 focus:ring-indigo-500"
              />
            </div>
          ) : (
            <div className="opacity-30">
              <span className="block text-slate-500 mb-1">Środek (Raw):</span>
              <input
                type="text"
                disabled
                placeholder="N/A"
                className="w-full p-1.5 bg-slate-950 border border-slate-850 rounded text-slate-650 font-mono text-center text-xs"
              />
            </div>
          )}
          
          <div>
            <span className="block text-slate-500 mb-1">Max (Raw):</span>
            <input
              type="number"
              placeholder="Domyślne"
              value={maxVal ?? ''}
              onChange={(e) => {
                const val = e.target.value === '' ? null : parseInt(e.target.value);
                if (isGas || (!isGas && !isBrake)) {
                  handleUpdateMapping(mappingKey, { rawMax: val });
                } else {
                  handleUpdateMapping(mappingKey, { rawMaxBrake: val } as any);
                }
              }}
              className="w-full p-1.5 bg-slate-950 border border-slate-800 rounded text-white font-mono text-center text-xs focus:outline-none focus:ring-1 focus:ring-indigo-500"
            />
          </div>
        </div>

        <div className="flex gap-2 items-center justify-between pt-1">
          <div className="text-[10px] text-slate-450">
            {isCalibrating && liveRawVal !== null ? (
              <span>{t('calib_live_val') || 'Wartość na żywo: '}<strong className="text-white font-mono">{liveRawVal}</strong></span>
            ) : (
              <span className="text-slate-600">{t('calib_live_idle') || 'Kliknij Start, by mierzyć'}</span>
            )}
          </div>
          
          <div className="flex gap-1.5">
            {!isCalibrating ? (
              <button
                type="button"
                onClick={() => startCalibration(subKey, deviceVal, axisVal)}
                className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-white rounded text-[10px] font-bold transition active:scale-95"
              >
                {t('calib_start') || 'Rozpocznij kalibrację'}
              </button>
            ) : (
              <>
                <button
                  type="button"
                  onClick={() => recordCalibPoint(subKey, 'min')}
                  className="px-2 py-1 bg-blue-600 hover:bg-blue-500 text-white rounded text-[10px] font-bold active:scale-95 transition"
                >
                  {t('calib_set_min') || 'Ustaw Min'}
                </button>
                {(!isBrake) && (
                  <button
                    type="button"
                    onClick={() => recordCalibPoint(subKey, 'center')}
                    className="px-2 py-1 bg-green-600 hover:bg-green-500 text-white rounded text-[10px] font-bold active:scale-95 transition"
                  >
                    {t('calib_set_center') || 'Ustaw Środek'}
                  </button>
                )}
                <button
                  type="button"
                  onClick={() => recordCalibPoint(subKey, 'max')}
                  className="px-2 py-1 bg-red-650 hover:bg-red-600 text-white rounded text-[10px] font-bold active:scale-95 transition"
                >
                  {t('calib_set_max') || 'Ustaw Max'}
                </button>
                <button
                  type="button"
                  onClick={stopCalibration}
                  className="px-2.5 py-1 bg-slate-700 hover:bg-slate-600 text-white rounded text-[10px] font-bold active:scale-95 transition"
                >
                  {t('calib_stop') || 'Zakończ'}
                </button>
              </>
            )}
            
            {hasAnyCalib && (
              <button
                type="button"
                onClick={() => {
                  if (isGas || (!isGas && !isBrake)) {
                    handleUpdateMapping(mappingKey, { rawMin: null, rawMax: null, rawCenter: null });
                  } else {
                    handleUpdateMapping(mappingKey, { rawMinBrake: null, rawMaxBrake: null } as any);
                  }
                }}
                className="px-2 py-1 bg-slate-950 hover:bg-red-950/40 text-slate-500 hover:text-red-400 border border-slate-855 hover:border-red-900/30 rounded text-[10px] transition active:scale-95"
              >
                {t('calib_reset') || 'Resetuj'}
              </button>
            )}
          </div>
        </div>
      </div>
    );
  };

  const getChannelLabel = (channelKey: string) => {
    const lowKey = channelKey.toLowerCase();
    if (lowKey === 'throttle') return t('channel_throttle') || 'Throttle';
    if (lowKey === 'aileron') return t('channel_aileron') || 'Aileron';
    if (lowKey === 'elevator') return t('channel_elevator') || 'Elevator';
    if (lowKey === 'rudder') return t('channel_rudder') || 'Rudder';
    return channelKey;
  };

  // Auto-Assign detector using backend API
  const handleStartDetect = async (key: string) => {
    setIsDetecting(key);
    setDetectStatus(t('wizard_detecting'));
    try {
      const res = await fetch('/api/wizard/detect?timeout=5.0');
      if (res.ok) {
        const data = await res.json();
        if (data.detected) {
          if (key === 'gearbox_up') {
            await handleUpdateGearboxConfig({ btn_up: data.axis });
          } else if (key === 'gearbox_down') {
            await handleUpdateGearboxConfig({ btn_down: data.axis });
          } else if (key === 'drive_mode_btn') {
            await handleUpdateProfileFields({ driveModeBtn: data.axis });
          } else if (key === 'cruise_btn') {
            await handleUpdateProfileFields({ cruiseBtn: data.axis });
          } else if (key === 'arm_btn') {
            await handleUpdateProfileFields({ armBtn: data.axis });
          } else {
            handleUpdateMapping(key, {
              device: data.device_name,
              axis: data.axis,
            });
          }
          setDetectStatus(`${t('wizard_success')} ${data.device_name} -> ${data.axis}`);
          setLogs(prev => [...prev, `[WIZARD] Przypisano automatycznie oś/przycisk dla ${key}: ${data.device_name} -> ${data.axis}`]);
          setTimeout(() => setIsDetecting(null), 1500);
        } else {
          setDetectStatus(t('wizard_timeout'));
          setTimeout(() => setIsDetecting(null), 2000);
        }
      } else {
        setDetectStatus(t('wizard_timeout'));
        setTimeout(() => setIsDetecting(null), 2000);
      }
    } catch (e) {
      setDetectStatus(t('wizard_timeout'));
      setTimeout(() => setIsDetecting(null), 2000);
    }
  };

  const renderExpoGraph = (expoValue: number) => {
    const width = 120;
    const height = 66;
    const points: string[] = [];

    for (let x = -1; x <= 1; x += 0.1) {
      const expoDecimal = expoValue / 100;
      const y = (1 - expoDecimal) * x + expoDecimal * Math.pow(x, 3);
      const svgX = ((x + 1) / 2) * width;
      const svgY = height - ((y + 1) / 2) * height;
      points.push(`${svgX},${svgY}`);
    }

    return (
      <svg width={width} height={height} className="border border-slate-800 rounded-lg bg-slate-950/85">
        <line x1={0} y1={height / 2} x2={width} y2={height / 2} stroke="#334155" strokeDasharray="2" />
        <line x1={width / 2} y1={0} x2={width / 2} y2={height} stroke="#334155" strokeDasharray="2" />
        <polyline fill="none" stroke="#6366f1" strokeWidth="2.5" points={points.join(' ')} />
        <text x="3" y="10" className="text-[8px] fill-slate-500 font-mono">-100%</text>
        <text x="94" y="10" className="text-[8px] fill-slate-500 font-mono">+100%</text>
      </svg>
    );
  };


  return (
    <div id="view-profile" className="space-y-6">
      {/* Sub-tab navigation selector */}
      <div className="flex bg-slate-900/60 p-1.5 rounded-xl border border-slate-800/80 gap-1.5 text-xs font-bold text-slate-400">
        <button
          onClick={() => setSubTab('mixers')}
          className={`flex-1 p-2 rounded-lg transition-all ${subTab === 'mixers' ? 'bg-indigo-650 text-white shadow-md' : 'hover:text-white hover:bg-slate-800/50'}`}
        >
          {t('subtab_mixers')}
        </button>
        <button
          onClick={() => setSubTab('gearbox')}
          className={`flex-1 p-2 rounded-lg transition-all ${subTab === 'gearbox' ? 'bg-indigo-650 text-white shadow-md' : 'hover:text-white hover:bg-slate-800/50'}`}
        >
          {t('subtab_gearbox')}
        </button>
        <button
          onClick={() => setSubTab('definitions')}
          className={`flex-1 p-2 rounded-lg transition-all ${subTab === 'definitions' ? 'bg-indigo-650 text-white shadow-md' : 'hover:text-white hover:bg-slate-800/50'}`}
        >
          {t('subtab_definitions')}
        </button>
        <button
          onClick={() => setSubTab('deadzones')}
          className={`flex-1 p-2 rounded-lg transition-all ${subTab === 'deadzones' ? 'bg-indigo-650 text-white shadow-md' : 'hover:text-white hover:bg-slate-800/50'}`}
        >
          {t('subtab_deadzones')}
        </button>
      </div>

      {/* SUB-TAB 1: MIXERS */}
      {subTab === 'mixers' && (
        <div className="bg-slate-900/40 backdrop-blur-md p-6 rounded-2xl border border-slate-800 shadow-xl">
          <div className="mb-6">
            <h2 className="text-lg font-black text-white flex items-center gap-2">
              <Sliders className="h-5 w-5 text-indigo-400 rotate-90" />
              {t('mixers_title')} (Profil: {currentProfile.name})
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              {t('mixers_desc')}
            </p>
          </div>

          <div className="overflow-x-auto border border-slate-800 rounded-xl bg-slate-950/20">
            <table className="w-full text-left border-collapse" id="matrix-mappings-table">
              <thead>
                <tr className="bg-slate-900/80 text-[10px] font-black uppercase text-slate-400 border-b border-slate-800">
                  <th className="p-3">{t('table_rc_signal')}</th>
                  <th className="p-3">{t('table_input_device')}</th>
                  <th className="p-3">{t('table_physical_axis')}</th>
                  <th className="p-3 text-center">{t('table_output_ch')}</th>
                  <th className="p-3 text-center">{t('table_reverse')}</th>
                  <th className="p-3 text-right">{t('table_actions')}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-850 text-xs text-slate-350">
                {Object.keys(currentProfile.mappings).flatMap((key) => {
                  const item = currentProfile.mappings[key];
                  
                  if (item.type === 'split_axis') {
                    // Generujemy dwa wirtualne wiersze na potrzeby podziału osi (Gaz / Hamulec)
                    const subKeys = [
                      { subKey: `${key}_gas`, displayName: `${key} (Gaz / Gas)`, axisVal: item.axis || '—', deviceVal: item.device },
                      { subKey: `${key}_brake`, displayName: `${key} (Hamulec / Brake)`, axisVal: (item as any).axisBrake || '—', deviceVal: (item as any).deviceBrake || 'None' }
                    ];

                    return subKeys.map(({ subKey, displayName, axisVal, deviceVal }) => {
                      const usbName = usbControllers.find((u) => u.id === deviceVal)?.name || deviceVal || t('none');
                      const isEditing = editingMappingKey === subKey;

                      return (
                        <React.Fragment key={subKey}>
                          <tr
                            id={`row-mapping-${subKey}`}
                            className={`hover:bg-slate-900/20 transition-colors duration-150 ${
                              isEditing ? 'bg-indigo-950/20 text-white font-semibold' : ''
                            }`}
                          >
                            <td className="p-3 font-bold flex items-center gap-2 text-white">
                              <Sliders className="h-3.5 w-3.5 text-indigo-400 rotate-90" />
                              {displayName}
                            </td>
                            <td className="p-3 font-mono text-slate-450">
                              {deviceVal === 'None' ? <span className="text-slate-600">{t('none')}</span> : usbName}
                            </td>
                            <td className="p-3 font-mono text-slate-450">{deviceVal === 'None' ? '—' : axisVal}</td>
                            <td className="p-3 text-center font-black text-indigo-400">CH {item.outputChannel}</td>
                            <td className="p-3 text-center">
                              <button
                                id={`reverse-switch-${subKey}`}
                                onClick={() => {
                                  if (subKey.endsWith('_gas')) {
                                    handleUpdateMapping(key, { reverse: !item.reverse });
                                  } else {
                                    handleUpdateMapping(key, { reverseBrake: !(item as any).reverseBrake } as any);
                                  }
                                }}
                                className={`relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${
                                  (subKey.endsWith('_gas') ? item.reverse : !!(item as any).reverseBrake) ? 'bg-indigo-650' : 'bg-slate-800'
                                }`}
                              >
                                <span
                                  className={`pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow-lg transition duration-200 ease-in-out ${
                                    (subKey.endsWith('_gas') ? item.reverse : !!(item as any).reverseBrake) ? 'translate-x-4' : 'translate-x-0'
                                  }`}
                                />
                              </button>
                            </td>
                            <td className="p-3 text-right">
                              <button
                                id={`edit-mapping-btn-${subKey}`}
                                onClick={() => setEditingMappingKey(isEditing ? null : subKey)}
                                className={`p-1.5 px-3 font-bold border rounded-lg transition text-[10px] ${
                                  isEditing
                                    ? 'bg-slate-800 border-slate-700 text-white'
                                    : 'bg-slate-900 hover:bg-indigo-950/30 hover:text-indigo-400 border-slate-800 hover:border-indigo-500/30 text-slate-400'
                                }`}
                              >
                                {isEditing ? t('close') : t('edit')}
                              </button>
                            </td>
                          </tr>

                          {isEditing && (
                            <tr className="bg-slate-950/40" id={`edit-panel-row-${subKey}`}>
                              <td colSpan={6} className="p-4 border-b border-indigo-950/50">
                                <div className="grid grid-cols-1 md:grid-cols-12 gap-6 text-xs">
                                  <div className="md:col-span-8 space-y-4">
                                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                                      <div>
                                        <label className="block text-[10px] font-bold uppercase text-slate-500 mb-1">
                                          {t('hid_controller')} ({subKey.endsWith('_gas') ? (t('is_english') === 'true' ? 'Gas' : 'Gaz') : (t('is_english') === 'true' ? 'Brake' : 'Hamulec')})
                                        </label>
                                        <div className="flex gap-2">
                                          <select
                                            id={`edit-input-device-${subKey}`}
                                            value={deviceVal}
                                            onChange={(e) => {
                                              if (subKey.endsWith('_gas')) {
                                                handleUpdateMapping(key, { device: e.target.value });
                                              } else {
                                                handleUpdateMapping(key, { deviceBrake: e.target.value } as any);
                                              }
                                            }}
                                            className="flex-1 p-2 bg-slate-900 border border-slate-800 rounded-lg text-xs text-white focus:outline-none focus:ring-1 focus:ring-indigo-500 min-w-0"
                                          >
                                            <option value="None">{t('none')}</option>
                                            {usbControllers.map((u) => (
                                              <option key={u.id} value={u.id}>
                                                {u.name}
                                              </option>
                                            ))}
                                          </select>
                                          <button
                                            type="button"
                                            onClick={async () => {
                                              setIsDetecting(subKey);
                                              setDetectStatus(t('wizard_detecting'));
                                              try {
                                                const res = await fetch('/api/wizard/detect?timeout=5.0');
                                                if (res.ok) {
                                                  const data = await res.json();
                                                  if (data.detected) {
                                                    if (subKey.endsWith('_gas')) {
                                                      handleUpdateMapping(key, { device: data.device_name, axis: data.axis });
                                                    } else {
                                                      handleUpdateMapping(key, { deviceBrake: data.device_name, axisBrake: data.axis } as any);
                                                    }
                                                    setDetectStatus(`${t('wizard_success')} ${data.device_name} -> ${data.axis}`);
                                                    setLogs(prev => [...prev, `[WIZARD] Przypisano automatycznie oś dla ${subKey}: ${data.device_name} -> ${data.axis}`]);
                                                    setTimeout(() => setIsDetecting(null), 1500);
                                                  } else {
                                                    setDetectStatus(t('wizard_timeout'));
                                                    setTimeout(() => setIsDetecting(null), 2000);
                                                  }
                                                } else {
                                                  setDetectStatus(t('wizard_timeout'));
                                                  setTimeout(() => setIsDetecting(null), 2000);
                                                }
                                              } catch (e) {
                                                setDetectStatus(t('wizard_timeout'));
                                                setTimeout(() => setIsDetecting(null), 2000);
                                              }
                                            }}
                                            className="p-2 bg-indigo-600 hover:bg-indigo-700 text-white font-bold rounded-lg text-xs flex items-center justify-center gap-1 active:scale-95 transition shrink-0"
                                          >
                                            <Target className="h-4 w-4" />
                                            {t('assign_btn')}
                                          </button>
                                        </div>
                                      </div>

                                      <div>
                                        <label className="block text-[10px] font-bold uppercase text-slate-500 mb-1">
                                          {t('axis_switch')}
                                        </label>
                                        <input
                                          id={`edit-input-axis-${subKey}`}
                                          type="text"
                                          value={axisVal}
                                          onChange={(e) => {
                                            if (subKey.endsWith('_gas')) {
                                              handleUpdateMapping(key, { axis: e.target.value });
                                            } else {
                                              handleUpdateMapping(key, { axisBrake: e.target.value } as any);
                                            }
                                          }}
                                          placeholder="np. ABS_Z lub ABS_RZ"
                                          className="w-full p-2 bg-slate-900 border border-slate-800 rounded-lg text-xs text-white font-mono focus:outline-none focus:ring-1 focus:ring-indigo-500"
                                          disabled={deviceVal === 'None'}
                                        />
                                      </div>
                                    </div>

                                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                                      <div>
                                        <label className="block text-[10px] font-bold uppercase text-slate-500 mb-1">
                                          {t('output_channel_label')}
                                        </label>
                                        <input
                                          id={`edit-output-channel-${subKey}`}
                                          type="number"
                                          disabled
                                          value={item.outputChannel}
                                          className="w-full p-2 bg-slate-900/50 border border-slate-800 rounded-lg text-xs font-mono text-slate-500"
                                        />
                                      </div>

                                      <div>
                                        <label className="block text-[10px] font-bold uppercase text-slate-500 mb-1">
                                          {t('subtrim_label')} ({subKey.endsWith('_gas') ? (t('is_english') === 'true' ? 'Gas' : 'Gaz') : (t('is_english') === 'true' ? 'Brake' : 'Hamulec')}): {subKey.endsWith('_gas') ? item.subTrim : ((item as any).subTrimBrake || 0)}us
                                        </label>
                                        <div className="flex items-center gap-2 mt-2">
                                          <span className="text-[9px] text-slate-500">-100us</span>
                                          <input
                                            id={`edit-subtrim-slider-${subKey}`}
                                            type="range"
                                            min="-100"
                                            max="100"
                                            value={subKey.endsWith('_gas') ? item.subTrim : ((item as any).subTrimBrake || 0)}
                                            onChange={(e) => {
                                              if (subKey.endsWith('_gas')) {
                                                handleUpdateMapping(key, { subTrim: parseInt(e.target.value) });
                                              } else {
                                                handleUpdateMapping(key, { subTrimBrake: parseInt(e.target.value) } as any);
                                              }
                                            }}
                                            className="flex-1 accent-indigo-500 h-1 bg-slate-800 rounded-lg appearance-none cursor-pointer"
                                          />
                                        </div>
                                      </div>
                                    </div>

                                    {/* Failsafe Settings row */}
                                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                                      <div>
                                        <label className="block text-[10px] font-bold uppercase text-slate-500 mb-1">
                                          {t('failsafe_mode_label')}
                                        </label>
                                        <select
                                          id={`edit-failsafe-mode-${subKey}`}
                                          value={item.failsafeMode || 'center'}
                                          onChange={(e) => handleUpdateMapping(key, { failsafeMode: e.target.value as any })}
                                          className="w-full p-2 bg-slate-900 border border-slate-800 rounded-lg text-xs text-white focus:outline-none focus:ring-1 focus:ring-indigo-500"
                                        >
                                          <option value="center">{t('failsafe_mode_center')}</option>
                                          <option value="hold">{t('failsafe_mode_hold')}</option>
                                          <option value="custom">{t('failsafe_mode_custom')}</option>
                                        </select>
                                      </div>

                                      {item.failsafeMode === 'custom' && (
                                        <div>
                                          <label className="block text-[10px] font-bold uppercase text-slate-500 mb-1">
                                            {t('failsafe_val_label')}: {item.failsafeValue ?? 1500}us
                                          </label>
                                          <div className="flex items-center gap-2 mt-2">
                                            <span className="text-[9px] text-slate-500">1000us</span>
                                            <input
                                              id={`edit-failsafe-value-slider-${subKey}`}
                                              type="range"
                                              min="1000"
                                              max="2000"
                                              value={item.failsafeValue ?? 1500}
                                              onChange={(e) => handleUpdateMapping(key, { failsafeValue: parseInt(e.target.value) })}
                                              className="flex-1 accent-indigo-500 h-1 bg-slate-800 rounded-lg appearance-none cursor-pointer"
                                            />
                                            <span className="text-[9px] text-slate-500">2000us</span>
                                          </div>
                                        </div>
                                      )}
                                    </div>

                                    {renderCalibrationUI(subKey, key, item, deviceVal, axisVal)}
                                  </div>

                                  <div className="md:col-span-4 flex flex-col items-center justify-between border-l border-slate-800/80 pl-4 py-2">
                                    <div className="w-full text-left space-y-1">
                                      <div className="flex justify-between items-center">
                                        <span className="text-[10px] font-bold uppercase text-slate-500">{t('expo_curve_label')}</span>
                                        <span className="text-xs font-black text-indigo-400 font-mono">{(subKey.endsWith('_gas') ? item.expo : ((item as any).expoBrake || 0))}%</span>
                                      </div>
                                      <p className="text-[10px] text-slate-500 mb-2 leading-tight">
                                        {t('expo_desc')}
                                      </p>
                                    </div>

                                    {renderExpoGraph(subKey.endsWith('_gas') ? item.expo : ((item as any).expoBrake || 0))}

                                    <div className="w-full mt-3">
                                      <input
                                        id={`edit-expo-slider-${subKey}`}
                                        type="range"
                                        min="0"
                                        max="100"
                                        value={subKey.endsWith('_gas') ? item.expo : ((item as any).expoBrake || 0)}
                                        onChange={(e) => {
                                          if (subKey.endsWith('_gas')) {
                                            handleUpdateMapping(key, { expo: parseInt(e.target.value) });
                                          } else {
                                            handleUpdateMapping(key, { expoBrake: parseInt(e.target.value) } as any);
                                          }
                                        }}
                                        className="w-full accent-indigo-500 h-1 bg-slate-800 rounded-lg appearance-none cursor-pointer"
                                      />
                                      <div className="flex justify-between text-[8px] text-slate-500 mt-1 font-mono uppercase">
                                        <span>{t('linear_label')}</span>
                                        <span>{t('max_label')}</span>
                                      </div>
                                    </div>
                                  </div>
                                </div>
                              </td>
                            </tr>
                          )}
                        </React.Fragment>
                      );
                    });
                  }

                  const usbName = usbControllers.find((u) => u.id === item.device)?.name || item.device || t('none');

                  return (
                    <React.Fragment key={key}>
                      <tr
                        id={`row-mapping-${key}`}
                        className={`hover:bg-slate-900/20 transition-colors duration-150 ${
                          editingMappingKey === key ? 'bg-indigo-950/20 text-white font-semibold' : ''
                        }`}
                      >
                        <td className="p-3 font-bold flex items-center gap-2 text-white">
                          <Sliders className="h-3.5 w-3.5 text-indigo-400 rotate-90" />
                          {getChannelLabel(key)}
                        </td>
                        <td className="p-3 font-mono text-slate-450">
                          {item.device === 'None' ? <span className="text-slate-600">{t('none')}</span> : usbName}
                        </td>
                        <td className="p-3 font-mono text-slate-450">{item.device === 'None' ? '—' : item.axis}</td>
                        <td className="p-3 text-center font-black text-indigo-400">CH {item.outputChannel}</td>
                        <td className="p-3 text-center">
                          <button
                            id={`reverse-switch-${key}`}
                            onClick={() => handleUpdateMapping(key, { reverse: !item.reverse })}
                            className={`relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${
                              item.reverse ? 'bg-indigo-650' : 'bg-slate-800'
                            }`}
                          >
                            <span
                              className={`pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow-lg transition duration-200 ease-in-out ${
                                item.reverse ? 'translate-x-4' : 'translate-x-0'
                              }`}
                            />
                          </button>
                        </td>
                        <td className="p-3 text-right">
                          <button
                            id={`edit-mapping-btn-${key}`}
                            onClick={() => setEditingMappingKey(editingMappingKey === key ? null : key)}
                            className={`p-1.5 px-3 font-bold border rounded-lg transition text-[10px] ${
                              editingMappingKey === key
                                ? 'bg-slate-800 border-slate-700 text-white'
                                : 'bg-slate-900 hover:bg-indigo-950/30 hover:text-indigo-400 border-slate-800 hover:border-indigo-500/30 text-slate-400'
                            }`}
                          >
                            {editingMappingKey === key ? t('close') : t('edit')}
                          </button>
                        </td>
                      </tr>

                      {editingMappingKey === key && (
                        <tr className="bg-slate-950/40" id={`edit-panel-row-${key}`}>
                          <td colSpan={6} className="p-4 border-b border-indigo-950/50">
                            <div className="grid grid-cols-1 md:grid-cols-12 gap-6 text-xs">
                              <div className="md:col-span-8 space-y-4">
                                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                                  <div>
                                    <label className="block text-[10px] font-bold uppercase text-slate-500 mb-1">
                                      {t('hid_controller')}
                                    </label>
                                    <div className="flex gap-2">
                                      <select
                                        id={`edit-input-device-${key}`}
                                        value={item.device}
                                        onChange={(e) => handleUpdateMapping(key, { device: e.target.value })}
                                        className="flex-1 p-2 bg-slate-900 border border-slate-800 rounded-lg text-xs text-white focus:outline-none focus:ring-1 focus:ring-indigo-500 min-w-0"
                                      >
                                        <option value="None">{t('none')}</option>
                                        {usbControllers.map((u) => (
                                          <option key={u.id} value={u.id}>
                                            {u.name}
                                          </option>
                                        ))}
                                      </select>
                                      <button
                                        type="button"
                                        onClick={() => handleStartDetect(key)}
                                        className="p-2 bg-indigo-600 hover:bg-indigo-700 text-white font-bold rounded-lg text-xs flex items-center justify-center gap-1 active:scale-95 transition shrink-0"
                                        title="Uruchom automatyczne wykrywanie ruchu kontrolera"
                                      >
                                        <Target className="h-4 w-4" />
                                        {t('assign_btn')}
                                      </button>
                                    </div>
                                  </div>

                                  <div>
                                    <label className="block text-[10px] font-bold uppercase text-slate-500 mb-1">
                                      {t('axis_switch')}
                                    </label>
                                    <input
                                      id={`edit-input-axis-${key}`}
                                      type="text"
                                      value={item.axis}
                                      onChange={(e) => handleUpdateMapping(key, { axis: e.target.value })}
                                      placeholder="np. ABS_X lub BTN_SOUTH"
                                      className="w-full p-2 bg-slate-900 border border-slate-800 rounded-lg text-xs text-white font-mono focus:outline-none focus:ring-1 focus:ring-indigo-500"
                                      disabled={item.device === 'None'}
                                    />
                                  </div>
                                </div>

                                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                                  <div>
                                    <label className="block text-[10px] font-bold uppercase text-slate-500 mb-1">
                                      {t('output_channel_label')}
                                    </label>
                                    <input
                                      id={`edit-output-channel-${key}`}
                                      type="number"
                                      min="1"
                                      max="16"
                                      value={item.outputChannel}
                                      onChange={(e) =>
                                        handleUpdateMapping(key, {
                                          outputChannel: Math.min(16, Math.max(1, parseInt(e.target.value) || 1)),
                                        })
                                      }
                                      className="w-full p-2 bg-slate-900 border border-slate-800 rounded-lg text-xs font-mono text-white focus:outline-none focus:ring-1 focus:ring-indigo-500"
                                    />
                                  </div>

                                  <div>
                                    <label className="block text-[10px] font-bold uppercase text-slate-500 mb-1">
                                      {t('subtrim_label')}: {item.subTrim}us
                                    </label>
                                    <div className="flex items-center gap-2 mt-2">
                                      <span className="text-[9px] text-slate-500">-100us</span>
                                      <input
                                        id={`edit-subtrim-slider-${key}`}
                                        type="range"
                                        min="-100"
                                        max="100"
                                        value={item.subTrim}
                                        onChange={(e) => handleUpdateMapping(key, { subTrim: parseInt(e.target.value) })}
                                        className="flex-1 accent-indigo-500 h-1 bg-slate-800 rounded-lg appearance-none cursor-pointer"
                                      />
                                      <span className="text-[9px] text-slate-500">+100us</span>
                                    </div>
                                  </div>
                                </div>

                                {/* Failsafe Settings row */}
                                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                                  <div>
                                    <label className="block text-[10px] font-bold uppercase text-slate-500 mb-1">
                                      {t('failsafe_mode_label')}
                                    </label>
                                    <select
                                      id={`edit-failsafe-mode-${key}`}
                                      value={item.failsafeMode || 'center'}
                                      onChange={(e) => handleUpdateMapping(key, { failsafeMode: e.target.value as any })}
                                      className="w-full p-2 bg-slate-900 border border-slate-800 rounded-lg text-xs text-white focus:outline-none focus:ring-1 focus:ring-indigo-500"
                                    >
                                      <option value="center">{t('failsafe_mode_center')}</option>
                                      <option value="hold">{t('failsafe_mode_hold')}</option>
                                      <option value="custom">{t('failsafe_mode_custom')}</option>
                                    </select>
                                  </div>

                                  {(item.failsafeMode === 'custom') && (
                                    <div>
                                      <label className="block text-[10px] font-bold uppercase text-slate-500 mb-1">
                                        {t('failsafe_val_label')}: {item.failsafeValue ?? 1500}us
                                      </label>
                                      <div className="flex items-center gap-2 mt-2">
                                        <span className="text-[9px] text-slate-500">1000us</span>
                                        <input
                                          id={`edit-failsafe-value-slider-${key}`}
                                          type="range"
                                          min="1000"
                                          max="2000"
                                          value={item.failsafeValue ?? 1500}
                                          onChange={(e) => handleUpdateMapping(key, { failsafeValue: parseInt(e.target.value) })}
                                          className="flex-1 accent-indigo-500 h-1 bg-slate-800 rounded-lg appearance-none cursor-pointer"
                                        />
                                        <span className="text-[9px] text-slate-500">2000us</span>
                                      </div>
                                    </div>
                                  )}
                                </div>

                                {renderCalibrationUI(key, key, item, item.device, item.axis)}
                              </div>

                              <div className="md:col-span-4 flex flex-col items-center justify-between border-l border-slate-800/80 pl-4 py-2">
                                <div className="w-full text-left space-y-1">
                                  <div className="flex justify-between items-center">
                                    <span className="text-[10px] font-bold uppercase text-slate-500">{t('expo_curve_label')}</span>
                                    <span className="text-xs font-black text-indigo-400 font-mono">{item.expo}%</span>
                                  </div>
                                  <p className="text-[10px] text-slate-500 mb-2 leading-tight">
                                    {t('expo_desc')}
                                  </p>
                                </div>

                                {renderExpoGraph(item.expo)}

                                <div className="w-full mt-3">
                                  <input
                                    id={`edit-expo-slider-${key}`}
                                    type="range"
                                    min="0"
                                    max="100"
                                    value={item.expo}
                                    onChange={(e) => handleUpdateMapping(key, { expo: parseInt(e.target.value) })}
                                    className="w-full accent-indigo-500 h-1 bg-slate-800 rounded-lg appearance-none cursor-pointer"
                                  />
                                  <div className="flex justify-between text-[8px] text-slate-500 mt-1 font-mono uppercase">
                                    <span>{t('linear_label')}</span>
                                    <span>{t('max_label')}</span>
                                  </div>
                                </div>
                              </div>
                            </div>
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* SUB-TAB: GEARBOX */}
      {subTab === 'gearbox' && (
        <div className="bg-slate-900/40 backdrop-blur-md p-6 rounded-2xl border border-slate-800 shadow-xl space-y-6">
          <div>
            <h2 className="text-lg font-black text-white flex items-center gap-2">
              <Sliders className="h-5 w-5 text-indigo-400" />
              {t('gearbox_title')} (Profil: {currentProfile.name})
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              {t('gearbox_desc')}
            </p>
          </div>

          <div className="p-4 bg-slate-950/40 border border-slate-800 rounded-xl space-y-5">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-[10px] font-bold uppercase text-slate-500 mb-2">
                  {t('gearbox_mode')}
                </label>
                <select
                  id="gearbox-mode-select"
                  value={currentProfile.gearboxConfig?.mode || 'none'}
                  onChange={(e) => handleUpdateGearboxConfig({ mode: e.target.value as any })}
                  className="w-full p-2.5 bg-slate-900 border border-slate-800 rounded-lg text-xs text-white focus:outline-none"
                >
                  <option value="none">{t('gearbox_mode_none')}</option>
                  <option value="sequential">{t('gearbox_mode_sequential')}</option>
                </select>
              </div>

              {currentProfile.gearboxConfig?.mode === 'sequential' && (
                <div>
                  <label className="block text-[10px] font-bold uppercase text-slate-500 mb-2">
                    {t('gearbox_gears_count')}
                  </label>
                  <input
                    id="gearbox-gears-count"
                    type="number"
                    min="1"
                    max="10"
                    value={currentProfile.gearboxConfig?.num_forward_gears || 3}
                    onChange={(e) => handleUpdateGearboxConfig({ num_forward_gears: Math.min(10, Math.max(1, parseInt(e.target.value) || 1)) })}
                    className="w-full p-2 bg-slate-900 border border-slate-800 rounded-lg text-xs font-mono text-white focus:outline-none focus:ring-1 focus:ring-indigo-500"
                  />
                </div>
              )}
            </div>

            {currentProfile.gearboxConfig?.mode === 'sequential' && (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pt-2">
                <div>
                  <label className="block text-[10px] font-bold uppercase text-slate-500 mb-1">
                    {t('gearbox_reverse_limit')}: {Math.round((currentProfile.gearboxConfig?.reverse_throttle_limit || 0.3) * 100)}%
                  </label>
                  <div className="flex items-center gap-2 mt-2">
                    <span className="text-[9px] text-slate-500">10%</span>
                    <input
                      id="gearbox-reverse-limit-slider"
                      type="range"
                      min="10"
                      max="100"
                      value={Math.round((currentProfile.gearboxConfig?.reverse_throttle_limit || 0.3) * 100)}
                      onChange={(e) => handleUpdateGearboxConfig({ reverse_throttle_limit: parseInt(e.target.value) / 100 })}
                      className="flex-1 accent-indigo-500 h-1 bg-slate-800 rounded-lg appearance-none cursor-pointer"
                    />
                    <span className="text-[9px] text-slate-500">100%</span>
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-[10px] font-bold uppercase text-slate-500 mb-1">
                      {t('gearbox_btn_up')}
                    </label>
                    <div className="flex gap-2">
                      <input
                        id="gearbox-btn-up-input"
                        type="text"
                        placeholder="np. BTN_WEST"
                        value={currentProfile.gearboxConfig?.btn_up || ''}
                        onChange={(e) => handleUpdateGearboxConfig({ btn_up: e.target.value })}
                        className="flex-1 p-2 bg-slate-900 border border-slate-800 rounded-lg text-xs font-mono text-white focus:outline-none min-w-0"
                      />
                      <button
                        type="button"
                        onClick={() => handleStartDetect('gearbox_up')}
                        className="p-2 bg-indigo-600 hover:bg-indigo-700 text-white font-bold rounded-lg text-xs flex items-center justify-center gap-1 active:scale-95 transition shrink-0"
                        title="Przypisz przycisk biegu w górę"
                      >
                        <Target className="h-4 w-4" />
                        {t('assign_btn')}
                      </button>
                    </div>
                  </div>

                  <div>
                    <label className="block text-[10px] font-bold uppercase text-slate-500 mb-1">
                      {t('gearbox_btn_down')}
                    </label>
                    <div className="flex gap-2">
                      <input
                        id="gearbox-btn-down-input"
                        type="text"
                        placeholder="np. BTN_EAST"
                        value={currentProfile.gearboxConfig?.btn_down || ''}
                        onChange={(e) => handleUpdateGearboxConfig({ btn_down: e.target.value })}
                        className="flex-1 p-2 bg-slate-900 border border-slate-800 rounded-lg text-xs font-mono text-white focus:outline-none min-w-0"
                      />
                      <button
                        type="button"
                        onClick={() => handleStartDetect('gearbox_down')}
                        className="p-2 bg-indigo-600 hover:bg-indigo-700 text-white font-bold rounded-lg text-xs flex items-center justify-center gap-1 active:scale-95 transition shrink-0"
                        title="Przypisz przycisk biegu w dół"
                      >
                        <Target className="h-4 w-4" />
                        {t('assign_btn')}
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* PRZYCISKI ASYSTENTÓW JAZDY (TRYB JAZDY & TEMPOMAT) */}
            <div className="border-t border-slate-800/80 pt-5 space-y-4">
              <h3 className="text-xs font-bold text-white uppercase tracking-wider">{t('is_english') === 'true' ? 'Driving Assistant Buttons' : 'Przyciski Asystentów Jazdy'}</h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <label className="block text-[10px] font-bold uppercase text-slate-500 mb-1">
                    {t('btn_drive_mode')}
                  </label>
                  <div className="flex gap-2">
                    <input
                      id="drive-mode-btn-input"
                      type="text"
                      placeholder="np. BTN_WEST"
                      value={currentProfile.driveModeBtn || ''}
                      onChange={(e) => handleUpdateProfileFields({ driveModeBtn: e.target.value })}
                      className="flex-1 p-2 bg-slate-900 border border-slate-800 rounded-lg text-xs font-mono text-white focus:outline-none min-w-0"
                    />
                    <button
                      type="button"
                      onClick={() => handleStartDetect('drive_mode_btn')}
                      className="p-2 bg-indigo-600 hover:bg-indigo-700 text-white font-bold rounded-lg text-xs flex items-center justify-center gap-1 active:scale-95 transition shrink-0"
                      title="Przypisz przycisk trybu jazdy"
                    >
                      <Target className="h-4 w-4" />
                      {t('assign_btn')}
                    </button>
                  </div>
                </div>

                <div>
                  <label className="block text-[10px] font-bold uppercase text-slate-500 mb-1">
                    {t('btn_cruise')}
                  </label>
                  <div className="flex gap-2">
                    <input
                      id="cruise-btn-input"
                      type="text"
                      placeholder="np. BTN_NORTH"
                      value={currentProfile.cruiseBtn || ''}
                      onChange={(e) => handleUpdateProfileFields({ cruiseBtn: e.target.value })}
                      className="flex-1 p-2 bg-slate-900 border border-slate-800 rounded-lg text-xs font-mono text-white focus:outline-none min-w-0"
                    />
                    <button
                      type="button"
                      onClick={() => handleStartDetect('cruise_btn')}
                      className="p-2 bg-indigo-650 hover:bg-indigo-700 text-white font-bold rounded-lg text-xs flex items-center justify-center gap-1 active:scale-95 transition shrink-0"
                      title="Przypisz przycisk tempomatu"
                    >
                      <Target className="h-4 w-4" />
                      {t('assign_btn')}
                    </button>
                  </div>
                </div>

                <div>
                  <label className="block text-[10px] font-bold uppercase text-slate-500 mb-1">
                    {t('btn_arm_assign')}
                  </label>
                  <div className="flex gap-2">
                    <input
                      id="arm-btn-input"
                      type="text"
                      placeholder="np. BTN_SOUTH"
                      value={currentProfile.armBtn || ''}
                      onChange={(e) => handleUpdateProfileFields({ armBtn: e.target.value })}
                      className="flex-1 p-2 bg-slate-900 border border-slate-800 rounded-lg text-xs font-mono text-white focus:outline-none min-w-0"
                    />
                    <button
                      type="button"
                      onClick={() => handleStartDetect('arm_btn')}
                      className="p-2 bg-indigo-600 hover:bg-indigo-700 text-white font-bold rounded-lg text-xs flex items-center justify-center gap-1 active:scale-95 transition shrink-0"
                      title="Przypisz przycisk uzbrojenia"
                    >
                      <Target className="h-4 w-4" />
                      {t('assign_btn')}
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* SUB-TAB 2: CHANNEL DEFINITIONS */}
      {subTab === 'definitions' && (
        <div className="bg-slate-900/40 backdrop-blur-md p-6 rounded-2xl border border-slate-800 shadow-xl space-y-6">
          <div>
            <h2 className="text-lg font-black text-white flex items-center gap-2">
              <Zap className="h-5 w-5 text-indigo-400" />
              {t('channel_definitions_title')}
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              {t('channel_definitions_desc')}
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {Object.keys(currentProfile.mappings).map((key) => {
              const item = currentProfile.mappings[key];
              return (
                <div key={key} className="p-4 bg-slate-950/40 border border-slate-800 rounded-xl space-y-3.5">
                  <div className="flex justify-between items-center border-b border-slate-850/80 pb-2">
                    <span className="font-bold text-white text-xs">{getChannelLabel(key)} (CH {item.outputChannel})</span>
                    <select
                      value={item.type || 'bidirectional'}
                      onChange={(e) => handleUpdateMapping(key, { type: e.target.value as any })}
                      className="text-[10px] bg-slate-900 text-slate-350 border border-slate-800 rounded p-1 font-bold focus:outline-none"
                    >
                      <option value="bidirectional">{t('is_english') === 'true' ? 'Bidirectional (Steering)' : 'Dwukierunkowa (np. Skręt)'}</option>
                      <option value="unidirectional">{t('is_english') === 'true' ? 'Unidirectional (Throttle)' : 'Jednokierunkowa (np. Gaz)'}</option>
                      <option value="split_axis">{t('is_english') === 'true' ? 'Split Axis (Gas/Brake)' : 'Oś Dzielona (np. Gaz/Ham.)'}</option>
                    </select>
                  </div>

                  <div className="grid grid-cols-2 gap-3 text-[11px] text-slate-400">
                    <div>
                      <span className="block mb-1">{t('is_english') === 'true' ? 'Min Range:' : 'Zakres Min:'}</span>
                      <input
                        type="number"
                        min="1000"
                        max="1450"
                        value={item.epaMin}
                        onChange={(e) => handleUpdateMapping(key, { epaMin: parseInt(e.target.value) || 1000 })}
                        className="w-full p-2 bg-slate-900 border border-slate-800 rounded-lg text-white font-mono"
                      />
                    </div>
                    <div>
                      <span className="block mb-1">{t('is_english') === 'true' ? 'Max Range:' : 'Zakres Max:'}</span>
                      <input
                        type="number"
                        min="1550"
                        max="2000"
                        value={item.epaMax}
                        onChange={(e) => handleUpdateMapping(key, { epaMax: parseInt(e.target.value) || 2000 })}
                        className="w-full p-2 bg-slate-900 border border-slate-800 rounded-lg text-white font-mono"
                      />
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          {/* FFB Auto-Center Configuration for mapped devices */}
          {Object.values(currentProfile.mappings)
            .map((m) => m.device)
            .filter((d, index, self) => d && d !== 'None' && d !== 'Brak' && self.indexOf(d) === index)
            .length > 0 && (
            <div className="bg-slate-950/40 p-4 border border-slate-800 rounded-xl space-y-4 mt-6">
              <div>
                <h3 className="text-xs font-bold text-white flex items-center gap-2">
                  <Target className="h-4 w-4 text-indigo-400" />
                  {t('ffb_autocenter_title') || (t('is_english') === 'true' ? 'Force Feedback (FFB) Auto-Center' : 'Auto-Center dla urządzeń z FFB')}
                </h3>
                <p className="text-[10px] text-slate-400 mt-0.5">
                  {t('ffb_autocenter_desc') || (t('is_english') === 'true' ? 'Configure force centering strength for physical steering wheels or flight sticks supporting Force Feedback.' : 'Skonfiguruj siłę centrowania (sprężyny powrotnej) dla kierownic lub joysticków obsługujących sprzętowe sprzężenie zwrotne FFB.')}
                </p>
              </div>

              <div className="space-y-4">
                {Object.values(currentProfile.mappings)
                  .map((m) => m.device)
                  .filter((d, index, self) => d && d !== 'None' && d !== 'Brak' && self.indexOf(d) === index)
                  .map(devName => {
                    const usbName = usbControllers.find(u => u.id === devName || u.name === devName)?.name || devName;
                    const currentStrength = currentProfile.ffbAutocenter?.[devName] ?? 0;
                    const currentRange = currentProfile.steeringRange?.[devName] ?? 900;
                    const currentHwRange = currentProfile.hardwareRange?.[devName] ?? 900;

                    return (
                      <div key={devName} className="p-3 bg-slate-900 border border-slate-850 rounded-lg space-y-4">
                        <div className="flex justify-between items-center text-[11px] font-mono border-b border-slate-800 pb-1.5">
                          <span className="font-bold text-white">{usbName}</span>
                        </div>

                        {/* Auto center slider */}
                        <div className="space-y-1">
                          <div className="flex justify-between text-[10px] text-slate-400 font-mono">
                            <span>{t('ffb_autocenter_title') || 'Siła centrowania (Auto-Center)'}</span>
                            <span className="text-indigo-400 font-bold font-mono">{currentStrength}%</span>
                          </div>
                          <div className="flex items-center gap-2">
                            <span className="text-[9px] text-slate-500">0%</span>
                            <input
                              type="range"
                              min="0"
                              max="100"
                              value={currentStrength}
                              onChange={(e) => {
                                const val = parseInt(e.target.value) || 0;
                                const updatedFfb = { ...(currentProfile.ffbAutocenter || {}), [devName]: val };
                                handleUpdateProfileFields({ ffbAutocenter: updatedFfb });
                              }}
                              className="flex-1 accent-indigo-500 h-1 bg-slate-800 rounded-lg appearance-none cursor-pointer"
                            />
                            <span className="text-[9px] text-slate-500">100%</span>
                          </div>
                        </div>

                        {/* Steering Range slider */}
                        <div className="space-y-1">
                          <div className="flex justify-between text-[10px] text-slate-400 font-mono">
                            <span>{t('steering_range_label') || (t('is_english') === 'true' ? 'Soft Lock Range (Max steering angle)' : 'Zakres Soft Lock (Maksymalny kąt skrętu)')}</span>
                            <span className="text-indigo-400 font-bold font-mono">{currentRange}°</span>
                          </div>
                          <div className="flex items-center gap-2">
                            <span className="text-[9px] text-slate-500">90°</span>
                            <input
                              type="range"
                              min="90"
                              max="1080"
                              step="10"
                              value={currentRange}
                              onChange={(e) => {
                                const val = parseInt(e.target.value) || 900;
                                const updatedRange = { ...(currentProfile.steeringRange || {}), [devName]: val };
                                handleUpdateProfileFields({ steeringRange: updatedRange });
                              }}
                              className="flex-1 accent-indigo-500 h-1 bg-slate-800 rounded-lg appearance-none cursor-pointer"
                            />
                            <span className="text-[9px] text-slate-500">1080°</span>
                          </div>
                        </div>

                        {/* Hardware Range slider */}
                        <div className="space-y-1">
                          <div className="flex justify-between text-[10px] text-slate-400 font-mono">
                            <span>{t('hardware_range_label') || (t('is_english') === 'true' ? 'Hardware Wheel Range' : 'Sprzętowy zakres kierownicy')}</span>
                            <span className="text-indigo-400 font-bold font-mono">{currentHwRange}°</span>
                          </div>
                          <div className="flex items-center gap-2">
                            <span className="text-[9px] text-slate-500">90°</span>
                            <input
                              type="range"
                              min="90"
                              max="1080"
                              step="10"
                              value={currentHwRange}
                              onChange={(e) => {
                                const val = parseInt(e.target.value) || 900;
                                const updatedHwRange = { ...(currentProfile.hardwareRange || {}), [devName]: val };
                                handleUpdateProfileFields({ hardwareRange: updatedHwRange });
                              }}
                              className="flex-1 accent-indigo-500 h-1 bg-slate-800 rounded-lg appearance-none cursor-pointer"
                            />
                            <span className="text-[9px] text-slate-500">1080°</span>
                          </div>
                        </div>
                      </div>
                    );
                  })}
              </div>
            </div>
          )}
        </div>
      )}

      {/* SUB-TAB 3: DEADZONES */}
      {subTab === 'deadzones' && (
        <div className="bg-slate-900/40 backdrop-blur-md p-6 rounded-2xl border border-slate-800 shadow-xl space-y-6">
          <div>
            <h2 className="text-lg font-black text-white flex items-center gap-2">
              <Target className="h-5 w-5 text-indigo-400" />
              {t('deadzones_title')}
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              {t('deadzones_desc')}
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {Object.keys(currentProfile.mappings).map((key) => {
              const item = currentProfile.mappings[key];
              const dz = item.deadzone || 20;

              return (
                <div key={key} className="p-4 bg-slate-950/40 border border-slate-850 rounded-xl flex flex-col justify-between gap-3">
                  <div className="flex justify-between items-center text-xs font-mono">
                    <span className="font-bold text-white">{key}</span>
                    <span className="text-indigo-400 font-bold font-mono">DZ: ± {dz} us</span>
                  </div>

                  <div className="relative w-full h-3 bg-slate-950 rounded-full overflow-hidden border border-slate-800">
                    <div className="absolute left-1/2 -translate-x-1/2 top-0 bottom-0 bg-indigo-500/25 z-10" style={{ width: `${(dz / 500) * 100}%` }}></div>
                    <div className="absolute left-1/2 top-0 bottom-0 w-0.5 bg-slate-700 z-20"></div>
                  </div>

                  <div className="flex justify-between items-center">
                    <span className="text-[10px] text-slate-500 font-mono">{t('tolerance_label')} {1500 - dz} - {1500 + dz} us</span>
                    <div className="flex items-center gap-1">
                      <button
                        onClick={() => handleUpdateMapping(key, { deadzone: Math.max(0, dz - 5) })}
                        className="w-7 h-7 bg-slate-900 border border-slate-800 text-white font-bold rounded-lg hover:bg-slate-800 active:scale-90 transition flex items-center justify-center text-sm"
                      >
                        -
                      </button>
                      <button
                        onClick={() => handleUpdateMapping(key, { deadzone: Math.min(100, dz + 5) })}
                        className="w-7 h-7 bg-slate-900 border border-slate-800 text-white font-bold rounded-lg hover:bg-slate-800 active:scale-90 transition flex items-center justify-center text-sm"
                      >
                        +
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Profiles Creator / Selector (Always show at bottom) */}
      <div className="bg-slate-900/40 backdrop-blur-md p-6 rounded-2xl border border-slate-800 shadow-xl">
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-6">
          <div>
            <h2 className="text-lg font-black text-white flex items-center gap-2">
              <FileText className="h-5 w-5 text-indigo-400" />
              {t('profile_management_title')}
            </h2>
            <p className="text-xs text-slate-400 mt-0.5 font-sans">
              {t('profile_management_desc')}
            </p>
          </div>

          <button
            id="create-new-profile-trigger-btn"
            onClick={() => setProfileFormOpen(!profileFormOpen)}
            className="w-full sm:w-auto p-2.5 px-4 bg-indigo-650 hover:bg-indigo-700 text-white font-bold text-xs rounded-xl shadow-lg flex items-center justify-center gap-2 active:scale-95 transition"
          >
            <Plus className="h-4 w-4" /> {t('new_profile_btn')}
          </button>
        </div>

        {profileFormOpen && (
          <form
            onSubmit={handleCreateProfile}
            className="mb-6 p-5 bg-slate-950/60 rounded-xl border border-slate-800 text-xs text-slate-350 space-y-4 shadow-inner"
            id="create-profile-form"
          >
            <h3 className="text-sm font-bold text-white flex items-center gap-1.5">
              <Plus className="h-4 w-4 text-indigo-400" />
              {t('new_profile_form_title')}
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-[10px] font-bold uppercase text-slate-500 mb-1">{t('profile_name_label')}</label>
                <input
                  id="new-profile-name-input"
                  type="text"
                  placeholder="np. Rover_Crawler_6S"
                  value={newProfileName}
                  onChange={(e) => setNewProfileName(e.target.value)}
                  className="w-full p-2.5 bg-slate-900 border border-slate-800 rounded-lg text-xs text-white focus:outline-none focus:ring-1 focus:ring-indigo-500"
                  required
                />
              </div>

              <div>
                <label className="block text-[10px] font-bold uppercase text-slate-500 mb-1">
                  {t('battery_type_label')}
                </label>
                <select
                  id="new-profile-battery-select"
                  value={newProfileBattery}
                  onChange={(e) => setNewProfileBattery(e.target.value)}
                  className="w-full p-2.5 bg-slate-900 border border-slate-800 rounded-lg text-xs text-white focus:outline-none"
                >
                  <option value="2S">2S (Pakiet 7.4V)</option>
                  <option value="3S">3S (Pakiet 11.1V)</option>
                  <option value="4S">4S (Pakiet 14.8V)</option>
                  <option value="6S">6S (Pakiet 22.2V)</option>
                </select>
              </div>
            </div>

            <div className="flex justify-end gap-2.5 pt-2">
              <button
                id="cancel-create-profile-btn"
                type="button"
                onClick={() => setProfileFormOpen(false)}
                className="p-2 px-4 bg-slate-805 hover:bg-slate-800 border border-slate-850 font-bold rounded-lg text-slate-450 transition"
              >
                {t('cancel_btn')}
              </button>
              <button
                id="submit-create-profile-btn"
                type="submit"
                className="p-2 px-5 bg-indigo-600 text-white font-bold rounded-lg hover:bg-indigo-700 transition"
              >
                {t('create_profile_btn')}
              </button>
            </div>
          </form>
        )}

        <div className="space-y-4">
          <div
            id="active-profile-details"
            className="p-4 bg-indigo-950/10 rounded-xl border border-indigo-950 flex flex-col md:flex-row justify-between items-start md:items-center gap-4"
          >
            <div>
              <span className="text-[9px] font-black text-indigo-400 uppercase bg-indigo-950 border border-indigo-900/50 px-2.5 py-1 rounded">
                {t('is_english') === 'true' ? 'Active Profile' : 'Aktywny Profil'}
              </span>
              <h3 className="text-lg font-black text-white mt-2">{currentProfile.name}</h3>
              <p className="text-xs text-slate-400 mt-1">
                {t('is_english') === 'true' ? 'Battery protection for package: ' : 'Zabezpieczenie baterii dla pakietu: '}{currentProfile.batteryType} LiPo
              </p>
            </div>

            <div className="flex gap-2 w-full md:w-auto">
              <button
                id="clone-profile-btn"
                onClick={handleCloneProfile}
                className="flex-1 md:flex-initial p-2 px-4 bg-slate-800 hover:bg-slate-700 border border-slate-700 text-xs font-bold rounded-lg flex items-center justify-center gap-1.5 transition text-white"
              >
                <Copy className="h-3.5 w-3.5" /> {t('clone_profile_btn')}
              </button>

              <button
                id="delete-profile-btn"
                onClick={handleDeleteProfile}
                className="flex-1 md:flex-initial p-2 px-4 bg-red-950/20 hover:bg-red-950/40 text-red-400 border border-red-900/50 hover:border-red-900 text-xs font-bold rounded-lg flex items-center justify-center gap-1.5 transition"
              >
                <Trash2 className="h-3.5 w-3.5" /> {t('delete_profile_btn')}
              </button>
            </div>
          </div>

          <div className="space-y-2.5">
            <p className="text-[10px] font-bold text-slate-500 uppercase tracking-wider pl-1">
              {t('is_english') === 'true' ? 'List of profiles on disk' : 'Lista profili na dysku'}
            </p>

            {profiles.map((p) => {
              const isCurrent = p.id === activeProfileId;
              return (
                <div
                  key={p.id}
                  id={`profile-card-item-${p.id}`}
                  onClick={() => {
                    setActiveProfileId(p.id);
                    setLogs((prev) => [...prev, `[STATUS] Aktywowano profil: **${p.name}**.`]);
                  }}
                  className={`p-4 rounded-xl border flex justify-between items-center transition-all cursor-pointer ${
                    isCurrent
                      ? 'bg-slate-900 border-indigo-500 shadow-lg ring-1 ring-indigo-500/20'
                      : 'bg-slate-955/30 border-slate-900 hover:bg-slate-900/40 hover:border-slate-800'
                  }`}
                >
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-extrabold text-sm text-white">{p.name}</span>
                      {isCurrent && (
                        <span className="text-[8px] bg-indigo-650 text-white px-2 py-0.5 rounded font-bold uppercase tracking-wider">
                          {t('is_english') === 'true' ? 'Active' : 'Aktywny'}
                        </span>
                      )}
                    </div>
                    <p className="text-[10px] text-slate-500 font-mono mt-1">
                      {t('is_english') === 'true' ? 'Battery package: ' : 'Pakiet zasilania: '}{p.batteryType} LiPo • {t('is_english') === 'true' ? 'Active mixes: ' : 'Aktywne miksy: '}{' '}
                      {Object.values(p.mappings).filter((m) => m.device !== 'None').length} /{' '}
                      {Object.keys(p.mappings).length}
                    </p>
                  </div>
                  <ChevronRight className={`h-5 w-5 text-slate-500 transition-transform ${isCurrent ? 'translate-x-1' : ''}`} />
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Auto-Assign detection modal */}
      {isDetecting && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-850 p-6 rounded-2xl max-w-sm w-full space-y-4 text-center shadow-2xl">
            <div className="w-12 h-12 bg-indigo-500/10 text-indigo-400 rounded-full flex items-center justify-center mx-auto animate-pulse">
              <Target className="h-6 w-6" />
            </div>
            <h3 className="text-white font-bold text-sm">{t('mapping_wizard_detect')}</h3>
            <p className="text-xs text-slate-400 leading-relaxed font-mono">
              {detectStatus}
            </p>
            <button
              onClick={() => setIsDetecting(null)}
              className="p-2 bg-slate-800 hover:bg-slate-700 text-slate-300 font-bold rounded-lg text-xs w-full transition"
            >
              {t('cancel_btn')}
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

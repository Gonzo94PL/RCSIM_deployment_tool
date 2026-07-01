'use client';

import React, { useState, useEffect } from 'react';
import { Bluetooth, RefreshCw, Trash2, Link, Link2Off } from 'lucide-react';
import { TranslationFunction } from '../hooks/useTranslation';

interface BluetoothDevice {
  mac: string;
  name: string;
  paired: boolean;
  connected: boolean;
  trusted: boolean;
}

interface BluetoothConfigProps {
  t: TranslationFunction;
  setLogs: React.Dispatch<React.SetStateAction<string[]>>;
}

export const BluetoothConfig: React.FC<BluetoothConfigProps> = ({ t, setLogs }) => {
  const [devices, setDevices] = useState<BluetoothDevice[]>([]);
  const [isScanning, setIsScanning] = useState(false);
  const [loadingDeviceMac, setLoadingDeviceMac] = useState<string | null>(null);

  const fetchDevices = async () => {
    try {
      const res = await fetch('/api/bluetooth/devices');
      if (res.ok) {
        const data = await res.json();
        setDevices(data);
      }
    } catch (e) {
      console.error("Błąd pobierania urządzeń Bluetooth:", e);
    }
  };

  const fetchScanStatus = async () => {
    try {
      const res = await fetch('/api/bluetooth/status');
      if (res.ok) {
        const data = await res.json();
        setIsScanning(data.scanning);
      }
    } catch (e) {}
  };

  useEffect(() => {
    Promise.resolve().then(() => {
      fetchDevices();
      fetchScanStatus();
    });

    const interval = setInterval(() => {
      fetchDevices();
      fetchScanStatus();
    }, 3000);

    return () => clearInterval(interval);
  }, []);

  const handleScan = async () => {
    if (isScanning) return;
    setIsScanning(true);
    setLogs(prev => [...prev, `[BLUETOOTH] Rozpoczęto skanowanie w poszukiwaniu urządzeń...`]);
    try {
      const res = await fetch('/api/bluetooth/scan', { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        setIsScanning(data.scanning);
      }
    } catch (e) {
      console.error("Błąd startu skanowania Bluetooth:", e);
      setIsScanning(false);
    }
  };

  const handlePair = async (mac: string, name: string) => {
    setLoadingDeviceMac(mac);
    setLogs(prev => [...prev, `[BLUETOOTH] Parowanie z ${name} (${mac})...`]);
    try {
      const res = await fetch(`/api/bluetooth/pair?mac=${encodeURIComponent(mac)}`, { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        if (data.status === 'success') {
          setLogs(prev => [...prev, `[BLUETOOTH] Pomyślnie sparowano i zaufano: ${name}.`]);
          // Po parowaniu automatycznie połącz
          handleConnect(mac, name);
        } else {
          setLogs(prev => [...prev, `[ERROR] Nie udało się sparować z ${name}.`]);
        }
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoadingDeviceMac(null);
      fetchDevices();
    }
  };

  const handleConnect = async (mac: string, name: string) => {
    setLoadingDeviceMac(mac);
    setLogs(prev => [...prev, `[BLUETOOTH] Łączenie z ${name}...`]);
    try {
      const res = await fetch(`/api/bluetooth/connect?mac=${encodeURIComponent(mac)}`, { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        if (data.status === 'success') {
          setLogs(prev => [...prev, `[BLUETOOTH] Połączono z ${name}.`]);
        } else {
          setLogs(prev => [...prev, `[ERROR] Błąd łączenia z ${name}.`]);
        }
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoadingDeviceMac(null);
      fetchDevices();
    }
  };

  const handleDisconnect = async (mac: string, name: string) => {
    setLoadingDeviceMac(mac);
    setLogs(prev => [...prev, `[BLUETOOTH] Rozłączanie ${name}...`]);
    try {
      const res = await fetch(`/api/bluetooth/disconnect?mac=${encodeURIComponent(mac)}`, { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        if (data.status === 'success') {
          setLogs(prev => [...prev, `[BLUETOOTH] Rozłączono ${name}.`]);
        } else {
          setLogs(prev => [...prev, `[ERROR] Błąd rozłączania ${name}.`]);
        }
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoadingDeviceMac(null);
      fetchDevices();
    }
  };

  const handleRemove = async (mac: string, name: string) => {
    if (!window.confirm(`Czy na pewno usunąć i zapomnieć urządzenie ${name}?`)) return;
    setLoadingDeviceMac(mac);
    setLogs(prev => [...prev, `[BLUETOOTH] Usuwanie urządzenia ${name}...`]);
    try {
      const res = await fetch(`/api/bluetooth/remove?mac=${encodeURIComponent(mac)}`, { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        if (data.status === 'success') {
          setLogs(prev => [...prev, `[BLUETOOTH] Usunięto urządzenie ${name}.`]);
        } else {
          setLogs(prev => [...prev, `[ERROR] Błąd usuwania ${name}.`]);
        }
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoadingDeviceMac(null);
      fetchDevices();
    }
  };

  const pairedDevices = devices.filter(d => d.paired);
  const availableDevices = devices.filter(d => !d.paired);

  return (
    <div id="view-bluetooth" className="space-y-6">
      <div className="bg-slate-900/40 backdrop-blur-md p-6 rounded-2xl border border-slate-800 shadow-xl space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h2 className="text-lg font-black text-white flex items-center gap-2">
              <Bluetooth className="h-5 w-5 text-blue-500 animate-pulse" />
              {t('bluetooth_title')}
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              {t('bluetooth_desc')}
            </p>
          </div>
          <button
            onClick={handleScan}
            disabled={isScanning}
            className={`flex items-center justify-center gap-2 p-2.5 px-6 rounded-xl font-bold text-xs text-white shadow-lg transition active:scale-95 ${
              isScanning
                ? 'bg-slate-800 cursor-not-allowed text-slate-500'
                : 'bg-indigo-600 hover:bg-indigo-700'
            }`}
          >
            <RefreshCw className={`h-4 w-4 ${isScanning ? 'animate-spin' : ''}`} />
            {isScanning ? t('bluetooth_scanning') : t('bluetooth_scan_btn')}
          </button>
        </div>

        <div className="grid grid-cols-1 gap-6">
          {/* PAIRED DEVICES */}
          <div className="space-y-3">
            <h3 className="text-[10px] font-bold text-slate-500 uppercase tracking-wider pl-1">
              {t('bluetooth_paired')}
            </h3>
            <div className="space-y-2">
              {pairedDevices.length === 0 ? (
                <div className="p-4 bg-slate-950/40 rounded-xl border border-slate-850 text-center text-xs text-slate-500">
                  {t('bluetooth_no_devices')}
                </div>
              ) : (
                pairedDevices.map(device => (
                  <div
                    key={device.mac}
                    className="flex items-center justify-between p-3.5 bg-slate-950/40 rounded-xl border border-slate-850 hover:border-slate-800 transition"
                  >
                    <div className="flex items-center gap-3">
                      <div className={`p-2 rounded-lg ${device.connected ? 'bg-blue-500/10 text-blue-400' : 'bg-slate-800 text-slate-500'}`}>
                        <Bluetooth className="h-4.5 w-4.5" />
                      </div>
                      <div>
                        <div className="text-xs font-bold text-white">{device.name}</div>
                        <div className="text-[10px] font-mono text-slate-500 mt-0.5">{device.mac}</div>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className={`text-[10px] font-black uppercase px-2 py-0.5 rounded border ${
                        device.connected
                          ? 'bg-blue-500/10 border-blue-500/20 text-blue-400'
                          : 'bg-slate-900 border-slate-800 text-slate-500'
                      }`}>
                        {device.connected ? t('bluetooth_status_connected') : t('bluetooth_status_disconnected')}
                      </span>
                      {device.connected ? (
                        <button
                          onClick={() => handleDisconnect(device.mac, device.name)}
                          disabled={loadingDeviceMac !== null}
                          className="p-2 bg-slate-900 hover:bg-slate-800 text-slate-400 hover:text-white rounded-lg transition"
                          title={t('bluetooth_disconnect')}
                        >
                          <Link2Off className="h-4 w-4" />
                        </button>
                      ) : (
                        <button
                          onClick={() => handleConnect(device.mac, device.name)}
                          disabled={loadingDeviceMac !== null}
                          className="p-2 bg-slate-900 hover:bg-slate-800 text-indigo-400 hover:text-indigo-300 rounded-lg transition"
                          title={t('bluetooth_connect')}
                        >
                          <Link className="h-4 w-4" />
                        </button>
                      )}
                      <button
                        onClick={() => handleRemove(device.mac, device.name)}
                        disabled={loadingDeviceMac !== null}
                        className="p-2 bg-red-950/20 hover:bg-red-950/40 text-red-400 hover:text-red-300 rounded-lg transition"
                        title={t('bluetooth_remove')}
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* AVAILABLE DEVICES */}
          <div className="space-y-3">
            <h3 className="text-[10px] font-bold text-slate-500 uppercase tracking-wider pl-1">
              {t('bluetooth_available')}
            </h3>
            <div className="space-y-2">
              {availableDevices.length === 0 ? (
                <div className="p-4 bg-slate-950/40 rounded-xl border border-slate-850 text-center text-xs text-slate-500">
                  {isScanning ? t('bluetooth_scanning') : t('bluetooth_no_devices')}
                </div>
              ) : (
                availableDevices.map(device => (
                  <div
                    key={device.mac}
                    className="flex items-center justify-between p-3.5 bg-slate-950/40 rounded-xl border border-slate-850 hover:border-slate-800 transition"
                  >
                    <div className="flex items-center gap-3">
                      <div className="p-2 rounded-lg bg-slate-800 text-slate-500">
                        <Bluetooth className="h-4.5 w-4.5" />
                      </div>
                      <div>
                        <div className="text-xs font-bold text-white">{device.name}</div>
                        <div className="text-[10px] font-mono text-slate-500 mt-0.5">{device.mac}</div>
                      </div>
                    </div>
                    <button
                      onClick={() => handlePair(device.mac, device.name)}
                      disabled={loadingDeviceMac !== null}
                      className="p-2 px-4 bg-indigo-600/10 hover:bg-indigo-600/20 text-indigo-400 hover:text-indigo-300 font-bold text-xs rounded-lg transition"
                    >
                      {t('bluetooth_pair')}
                    </button>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

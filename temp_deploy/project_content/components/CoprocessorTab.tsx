'use client';

import React, { useRef } from 'react';
import { Cpu, Zap, Terminal as TerminalIcon, RotateCcw, XCircle, CheckCircle2, Upload, Trash2 } from 'lucide-react';
import { TranslationFunction } from '../hooks/useTranslation';

interface CoprocessorTabProps {
  otaState: 'idle' | 'uploading' | 'waiting_reset' | 'verifying' | 'writing' | 'success' | 'error';
  otaProgress: number;
  otaLogs: string[];
  selectedFirmwareFile: string;
  setSelectedFirmwareFile: (val: string) => void;
  firmwareTarget: 'esp32' | 'stm32' | 'xiao_rp2350';
  setFirmwareTarget: (val: 'esp32' | 'stm32' | 'xiao_rp2350') => void;
  uploadedFile: File | null;
  setUploadedFile: (val: File | null) => void;
  handleTriggerOta: () => void;
  handleCompileOta: () => void;
  logs: string[];
  otaScrollRef: React.RefObject<HTMLDivElement | null>;
  uartScrollRef: React.RefObject<HTMLDivElement | null>;
  showResetModal: boolean;
  onResetConfirmed: () => void;
  onResetCancel: () => void;
  t: TranslationFunction;
  clearOtaState?: () => void;
}

export const CoprocessorTab: React.FC<CoprocessorTabProps> = ({
  otaState,
  otaProgress,
  otaLogs,
  selectedFirmwareFile,
  setSelectedFirmwareFile,
  firmwareTarget,
  setFirmwareTarget,
  uploadedFile,
  setUploadedFile,
  handleTriggerOta,
  handleCompileOta,
  logs,
  otaScrollRef,
  uartScrollRef,
  showResetModal,
  onResetConfirmed,
  onResetCancel,
  t,
  clearOtaState,
}) => {
  const isActive = otaState === 'uploading' || otaState === 'waiting_reset' || otaState === 'verifying' || otaState === 'writing';
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setUploadedFile(e.target.files[0]);
    }
  };

  const handleRemoveFile = () => {
    setUploadedFile(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  return (
    <div id="view-coprocessor" className="space-y-6">

      {/* ──────────── Modal: Naciśnij RESET ──────────── */}
      {showResetModal && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center"
          style={{ background: 'rgba(0,0,0,0.75)', backdropFilter: 'blur(6px)' }}
          role="dialog"
          aria-modal="true"
          aria-labelledby="reset-modal-title"
        >
          <div
            className="relative w-full max-w-md mx-4 rounded-2xl border border-amber-500/40 shadow-2xl overflow-hidden"
            style={{ background: 'linear-gradient(135deg, #1e1b12 0%, #23200e 100%)' }}
          >
            {/* Pasek tytułowy */}
            <div className="flex items-center gap-3 px-6 pt-6 pb-4 border-b border-amber-500/20">
              <span className="relative flex h-4 w-4">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-4 w-4 bg-amber-500"></span>
              </span>
              <h2 id="reset-modal-title" className="text-base font-black text-amber-300 uppercase tracking-wider">
                {t('reset_modal_title')}
              </h2>
            </div>

            {/* Treść */}
            <div className="px-6 py-5 space-y-5">
              {/* Kroki */}
              <div className="space-y-3">
                <div className="flex items-start gap-3 p-3 rounded-xl bg-green-900/30 border border-green-700/40">
                  <CheckCircle2 className="h-5 w-5 text-green-400 mt-0.5 shrink-0" />
                  <div>
                    <p className="text-xs font-bold text-green-300 uppercase tracking-wide">{t('reset_step1_title')}</p>
                    <p className="text-[11px] text-green-200/80 mt-0.5">
                      {t('reset_step1_desc')}
                    </p>
                  </div>
                </div>

                <div className="flex items-start gap-3 p-3 rounded-xl bg-amber-900/30 border border-amber-500/50 shadow-[0_0_12px_rgba(245,158,11,0.15)]">
                  <RotateCcw className="h-5 w-5 text-amber-400 mt-0.5 shrink-0 animate-spin" style={{ animationDuration: '2s' }} />
                  <div>
                    <p className="text-xs font-bold text-amber-300 uppercase tracking-wide">{t('reset_step2_title')}</p>
                    <p className="text-[13px] text-amber-100 font-semibold mt-1">
                      {t('reset_step2_desc')}
                    </p>
                    <p className="text-[10px] text-amber-200/60 mt-1.5 leading-relaxed">
                      {t('reset_step2_info')}
                    </p>
                  </div>
                </div>

                <div className="flex items-start gap-3 p-3 rounded-xl bg-slate-800/40 border border-slate-700/40">
                  <Zap className="h-5 w-5 text-indigo-400/50 mt-0.5 shrink-0" />
                  <div>
                    <p className="text-xs font-bold text-slate-500 uppercase tracking-wide">{t('reset_step3_title')}</p>
                    <p className="text-[11px] text-slate-500 mt-0.5">
                      {t('reset_step3_desc')}
                    </p>
                  </div>
                </div>
              </div>

              {/* Przyciski akcji */}
              <div className="flex gap-3 pt-2">
                <button
                  id="reset-modal-confirm-btn"
                  onClick={onResetConfirmed}
                  className="flex-1 flex items-center justify-center gap-2 px-4 py-3 bg-amber-500 hover:bg-amber-400 active:scale-95 text-black font-black text-sm rounded-xl transition shadow-lg shadow-amber-500/30"
                >
                  <CheckCircle2 className="h-4 w-4" />
                  {t('reset_btn_confirmed')}
                </button>
                <button
                  id="reset-modal-cancel-btn"
                  onClick={onResetCancel}
                  className="flex items-center justify-center gap-1.5 px-4 py-3 bg-slate-800 hover:bg-slate-700 active:scale-95 text-slate-300 font-semibold text-sm rounded-xl transition border border-slate-700"
                >
                  <XCircle className="h-4 w-4 text-red-400" />
                  {t('cancel')}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ──────────── Panel Flash Koprocesora ──────────── */}
      <div className="bg-slate-900/40 backdrop-blur-md p-6 rounded-2xl border border-slate-800 shadow-xl">
        <div className="flex items-center gap-2 mb-4">
          <Cpu className="h-5 w-5 text-indigo-400" />
          <h2 className="text-lg font-black text-white">{t('coprocessor_prog_title')}</h2>
        </div>
        <p className="text-xs text-slate-400 mb-6 leading-relaxed">
          {t('coprocessor_prog_desc')}
        </p>

        <div className="grid grid-cols-1 md:grid-cols-12 gap-6 items-start">
          <div className="md:col-span-4 space-y-4 text-xs text-slate-350">
            {/* Wybór platformy (ESP32 lub STM32) */}
            <div>
              <label className="block text-[10px] font-bold uppercase text-slate-500 mb-1">
                {t('target_mcu')}
              </label>
              <select
                id="ota-target-select"
                value={firmwareTarget}
                onChange={(e) => setFirmwareTarget(e.target.value as 'esp32' | 'stm32' | 'xiao_rp2350')}
                className="w-full p-2.5 bg-slate-900 border border-slate-800 rounded-lg text-white font-mono focus:outline-none"
                disabled={isActive}
              >
                <option value="xiao_rp2350">XIAO RP2350 (USB-C / picotool)</option>
                <option value="stm32">STM32F103 (Blue Pill - OpenOCD)</option>
                <option value="esp32">ESP32 (Co-Processor - esptool)</option>
              </select>
            </div>

            {/* Wybór pliku */}
            <div>
              <label className="block text-[10px] font-bold uppercase text-slate-500 mb-1">
                {t('firmware_file')}
              </label>
              
              {/* Ukryty input do przesyłu pliku */}
              <input
                type="file"
                ref={fileInputRef}
                onChange={handleFileChange}
                accept=".bin,.hex,.uf2"
                className="hidden"
                disabled={isActive}
              />

              {uploadedFile ? (
                <div className="flex items-center justify-between p-2 bg-indigo-950/40 border border-indigo-500/35 rounded-lg">
                  <div className="truncate pr-2 font-mono text-indigo-200">
                    {uploadedFile.name}
                  </div>
                  <button
                    type="button"
                    onClick={handleRemoveFile}
                    className="p-1 bg-red-950/40 hover:bg-red-900/40 text-red-400 rounded transition"
                    title="Usuń plik"
                    disabled={isActive}
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </div>
              ) : (
                <div className="space-y-2">
                  <button
                    type="button"
                    onClick={() => fileInputRef.current?.click()}
                    className="w-full p-2.5 bg-slate-950 border border-slate-800 border-dashed hover:border-slate-700 hover:bg-slate-900/60 rounded-lg text-slate-400 font-bold flex items-center justify-center gap-1.5 transition"
                    disabled={isActive}
                  >
                    <Upload className="h-3.5 w-3.5 text-indigo-400" />
                    {t('select_from_pc')}
                  </button>

                  <select
                    id="ota-firmware-file-select"
                    value={selectedFirmwareFile}
                    onChange={(e) => setSelectedFirmwareFile(e.target.value)}
                    className="w-full p-2.5 bg-slate-900 border border-slate-800 rounded-lg text-white font-mono focus:outline-none text-[11px]"
                    disabled={isActive}
                  >
                    <option value="firmware.bin">{t('firmware_custom')}</option>
                    <option value="firmware_v1.4.2_esp32.bin">{t('firmware_stable')}</option>
                    <option value="firmware_v1.5.0_beta1.bin">{t('firmware_beta')}</option>
                    <option value="firmware_safe_recovery.bin">{t('firmware_recovery')}</option>
                  </select>
                </div>
              )}
            </div>

            {/* Status badge */}
            {otaState === 'waiting_reset' && (
              <div className="flex items-center gap-2 p-2.5 rounded-lg bg-amber-900/30 border border-amber-500/40 text-amber-300 text-[11px] font-semibold">
                <span className="relative flex h-2.5 w-2.5">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-amber-500"></span>
                </span>
                {t('waiting_reset')}
              </div>
            )}
            {otaState === 'writing' && (
              <div className="flex items-center gap-2 p-2.5 rounded-lg bg-indigo-900/30 border border-indigo-500/40 text-indigo-300 text-[11px] font-semibold">
                <span className="relative flex h-2.5 w-2.5">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-indigo-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-indigo-500"></span>
                </span>
                {t('flashing_progress')}
              </div>
            )}
            {otaState === 'success' && (
              <div className="flex items-center justify-between p-2.5 rounded-lg bg-green-900/30 border border-green-500/40 text-green-300 text-[11px] font-bold">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="h-3.5 w-3.5" />
                  {t('flash_success')}
                </div>
                {clearOtaState && (
                  <button
                    onClick={clearOtaState}
                    className="px-2 py-0.5 bg-green-950/80 hover:bg-green-900/80 text-[10px] text-green-300 rounded border border-green-700/50 transition cursor-pointer"
                  >
                    {t('monitor_uart')}
                  </button>
                )}
              </div>
            )}
            {otaState === 'error' && (
              <div className="flex items-center justify-between p-2.5 rounded-lg bg-red-900/30 border border-red-500/40 text-red-300 text-[11px] font-bold">
                <div className="flex items-center gap-2">
                  <XCircle className="h-3.5 w-3.5" />
                  {t('flash_error')}
                </div>
                {clearOtaState && (
                  <button
                    onClick={clearOtaState}
                    className="px-2 py-0.5 bg-red-950/80 hover:bg-red-900/80 text-[10px] text-red-300 rounded border border-red-700/50 transition cursor-pointer"
                  >
                    {t('clear')}
                  </button>
                )}
              </div>
            )}

            {(firmwareTarget === 'stm32' || firmwareTarget === 'xiao_rp2350') && (
              <button
                id="trigger-compile-btn"
                onClick={handleCompileOta}
                disabled={isActive}
                className={`w-full p-3 bg-slate-800 hover:bg-slate-750 text-slate-200 font-bold rounded-xl flex items-center justify-center gap-2 active:scale-95 transition border border-slate-700 shadow-md ${
                  isActive ? 'opacity-50 cursor-not-allowed' : ''
                }`}
              >
                <Cpu className="h-4 w-4 text-indigo-400" />
                {otaState === 'idle'
                  ? firmwareTarget === 'xiao_rp2350'
                    ? t('compile_rp2350')
                    : t('compile_generic')
                  : t('operation_in_progress')}
              </button>
            )}

            <button
              id="trigger-ota-btn"
              onClick={handleTriggerOta}
              disabled={isActive}
              className={`w-full p-3 bg-indigo-600 hover:bg-indigo-500 text-white font-bold rounded-xl flex items-center justify-center gap-2 active:scale-95 transition shadow-lg ${
                isActive ? 'opacity-50 cursor-not-allowed' : ''
              }`}
            >
              <Zap className="h-4 w-4" />
              {otaState === 'idle' ? `${t('flash_to')} ${firmwareTarget.toUpperCase()}` : t('operation_in_progress')}
            </button>

            {isActive && (
              <div className="space-y-1.5" id="ota-progress-box">
                <div className="flex justify-between text-[10px] font-bold text-slate-400">
                  <span>{t('esptool_progress')}</span>
                  <span className="font-mono">{otaProgress}%</span>
                </div>
                <div className="w-full bg-slate-950 rounded-full h-2 overflow-hidden border border-slate-800">
                  <div
                    className="bg-gradient-to-r from-indigo-500 to-cyan-400 h-full transition-all duration-300 rounded-full shadow-[0_0_8px_rgba(99,102,241,0.5)]"
                    style={{ width: `${otaProgress}%` }}
                  ></div>
                </div>
              </div>
            )}
          </div>

          <div className="md:col-span-8 space-y-2">
            <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider pl-1">
              {t('programmer_console')}
            </span>
            <div
              ref={otaScrollRef}
              className="w-full h-56 bg-slate-955/90 border border-slate-850 p-3 rounded-xl font-mono text-[10px] text-slate-300 overflow-y-auto space-y-1 shadow-inner scrollbar-thin scrollbar-thumb-slate-800"
              id="ota-logs-terminal"
            >
              {otaLogs.length === 0 ? (
                <p className="text-slate-600 italic">{t('waiting_flash_start')}</p>
              ) : (
                otaLogs.map((log, index) => <p key={index}>{log}</p>)
              )}
            </div>
          </div>
        </div>
      </div>

      {/* ──────────── Main Console UART Logs ──────────── */}
      <div className="bg-slate-900/40 backdrop-blur-md p-6 rounded-2xl border border-slate-800 shadow-xl">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <TerminalIcon className="h-5 w-5 text-indigo-400" />
            <h3 className="text-sm font-black text-white uppercase tracking-wider">
              {t('sys_diag_header')}
            </h3>
          </div>
          <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse"></span>
        </div>
        <p className="text-xs text-slate-400 mb-4 leading-relaxed">
          {t('sys_diag_desc')}
        </p>

        <div
          ref={uartScrollRef}
          className="w-full h-52 bg-slate-955/95 border border-slate-850 p-4 rounded-xl font-mono text-[10.5px] text-slate-355 overflow-y-auto space-y-1.5 shadow-inner scrollbar-thin scrollbar-thumb-slate-800"
          id="system-logs-terminal"
        >
          {logs.map((log, index) => {
            let colorClass = 'text-slate-300';
            if (log.includes('[SYSTEM]')) colorClass = 'text-indigo-400 font-bold';
            if (log.includes('[WARN]')) colorClass = 'text-amber-400 font-semibold';
            if (log.includes('[ERROR]')) colorClass = 'text-red-400 font-black';
            if (log.includes('[STATUS]')) colorClass = 'text-emerald-400 font-medium';

            return (
              <p key={index} className={colorClass}>
                {log}
              </p>
            );
          })}
        </div>
      </div>
    </div>
  );
};


import { useState, useEffect } from 'react';
import { translations, Language } from '../lib/translations';

export function useTranslation() {
  const [lang, setLangState] = useState<Language>('pl');

  // Load language preference from localStorage or backend config
  useEffect(() => {
    const localLang = localStorage.getItem('rcsim_lang') as Language | null;
    if (localLang && (localLang === 'pl' || localLang === 'en')) {
      setLangState(localLang);
    }
  }, []);

  const changeLanguage = (newLang: Language) => {
    setLangState(newLang);
    localStorage.setItem('rcsim_lang', newLang);
  };

  const t = (key: keyof typeof translations['pl']): string => {
    // Falls back to Polish translation if key is missing in selected language
    return translations[lang]?.[key] || translations['pl']?.[key] || key;
  };

  return {
    t,
    lang,
    setLang: changeLanguage,
  };
}
export type TranslationFunction = ReturnType<typeof useTranslation>['t'];

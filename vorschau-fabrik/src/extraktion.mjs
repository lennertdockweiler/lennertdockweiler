// Fakten aus Website-Texten ziehen (Impressum, Startseite, Über uns).
// Nur, was eindeutig dasteht – im Zweifel lieber nichts übernehmen.

const JETZT = new Date().getFullYear();

const RECHTSFORMEN = [
  [/\bGmbH\s*&\s*Co\.?\s*KG\b/i, 'GmbH & Co. KG'],
  [/\bUG\s*\(haftungsbeschr(?:ä|ae)nkt\)/i, 'UG (haftungsbeschränkt)'],
  [/\bgGmbH\b/i, 'gGmbH'],
  [/\bGmbH\b/i, 'GmbH'],
  [/\bAG\b/, 'AG'],
  [/\bOHG\b/i, 'OHG'],
  [/\bKG\b/, 'KG'],
  [/\be\.\s?K\.?(?=\s|$|,)/i, 'e. K.'],
  [/\be\.\s?Kfm\.?/i, 'e. Kfm.'],
  [/\bGbR\b/i, 'GbR'],
  [/\bUG\b/, 'UG (haftungsbeschränkt)'],
];

export function rechtsformAus(text) {
  for (const [re, name] of RECHTSFORMEN) if (re.test(text ?? '')) return name;
  return undefined;
}

/** Kurzname für Wortmarke/Logo (max. 32 Zeichen): Rechtsform und Inhaber-Zusätze entfernen */
export function kurznameAus(name) {
  let s = String(name)
    .replace(/\s*[-–,]?\s*Inh(?:aber|\.)(?:in)?\.?\s*[:]?\s*.+$/i, '')
    .replace(/\bGmbH\s*&\s*Co\.?\s*KG\b/gi, '')
    .replace(/\bUG\s*\(haftungsbeschr(?:ä|ae)nkt\)/gi, '')
    .replace(/\b(gGmbH|GmbH|AG|OHG|KG|GbR|UG|mbH)\b/g, '')
    .replace(/\be\.\s?K(?:fm)?\.?(?=\s|$)/gi, '')
    .replace(/\s{2,}/g, ' ')
    .replace(/[\s,&+-]+$/g, '')
    .trim();
  if (s.length <= 32) return s;
  const woerter = s.split(' ');
  // Vornamen in der Mitte weglassen („Malerbetrieb Hans Peter Schmidt“ → „Malerbetrieb Schmidt“)
  while (woerter.length > 2 && woerter.join(' ').length > 32) woerter.splice(woerter.length - 2, 1);
  s = woerter.join(' ');
  return s.length <= 32 ? s : s.slice(0, 32).replace(/\s+\S*$/, '').trim();
}

const NAME_RE = /^(?:(?:Dr|Prof|Dipl)\.(?:-\w+\.?)?\s+)*[A-ZÄÖÜ][a-zäöüß]+(?:-[A-ZÄÖÜ][a-zäöüß]+)?(?:\s+(?:von|van|de|zu|vom)\s+|\s+)[A-ZÄÖÜ][a-zäöüß]+(?:-[A-ZÄÖÜ][a-zäöüß]+)?(?:\s+[A-ZÄÖÜ][a-zäöüß]+)?$/;

function erstePerson(kandidaten) {
  for (let k of kandidaten) {
    for (let i = 0; i < 3; i++) {
      k = k
        .trim()
        .replace(/^(den|die|der|das|durch)\s+/i, '')
        .replace(/^(Geschäftsführ(?:er|erin|ung)|Inhaber(?:in)?|Vorstand|Betreiber(?:in)?|Inhaber und Geschäftsführer)\s*:?\s*/i, '');
    }
    k = k
      .replace(/\(.*?\)/g, '')
      .replace(/\b(Herr|Frau|Hr\.|Fr\.)\s+/g, '')
      .replace(/\s+(und|&|sowie)\s+.*$/i, '')
      .replace(/[,;|].*$/, '')
      .trim();
    if (NAME_RE.test(k) && k.length <= 60) return k;
  }
  return undefined;
}

/** Inhaber/Geschäftsführer aus dem Impressum */
export function inhaberAus(text) {
  if (!text) return undefined;
  const kandidaten = [];
  const re = /(Inhaber(?:in)?|Geschäftsführ(?:er|erin|ung)|Vertreten durch|Vertretungsberechtigt(?:e[rn]?)?(?:\s+Geschäftsführer(?:in)?)?|Betreiber(?:in)?)\s*[:.]?\s*\n?\s*([^\n]{3,80})/gi;
  for (const m of text.matchAll(re)) kandidaten.push(m[2]);
  return erstePerson(kandidaten);
}

export function emailAus(text) {
  if (!text) return undefined;
  const t = text.replace(/\s*(?:\(at\)|\[at\]|\{at\}| at )\s*/gi, '@').replace(/\s*(?:\(dot\)|\[dot\]|\(punkt\)|\[punkt\])\s*/gi, '.');
  const m = t.match(/[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}/g) ?? [];
  const gut = m.filter((e) => !/\.(png|jpe?g|gif|svg|webp)$/i.test(e) && !/example|sentry|wixpress|domain\.de/i.test(e));
  return gut[0]?.toLowerCase();
}

export function telefonAus(text) {
  if (!text) return undefined;
  const m = /(?:Tel(?:efon)?|Fon|Phone|Telefonnummer)\.?\s*[:.]?\s*([+0(][\d\s()/.-]{6,22}\d)/i.exec(text);
  return m?.[1]?.trim();
}

export function gruendungsjahrAus(...texte) {
  const jahre = [];
  for (const t of texte) {
    if (!t) continue;
    for (const m of t.matchAll(/\b(?:seit|gegründet(?:\s+(?:im\s+)?(?:Jahr(?:e)?)?)?|Gründung(?:sjahr)?\s*:?|est\.?|founded(?:\s+in)?)\s*(?:dem\s+Jahr(?:e)?\s*)?(1[89]\d\d|20[0-2]\d)\b/gi)) {
      const j = Number(m[1]);
      if (j >= 1850 && j <= JETZT) jahre.push(j);
    }
  }
  return jahre.length ? Math.min(...jahre) : undefined;
}

export function meisterAus(...texte) {
  const t = texte.filter(Boolean).join('\n');
  const betrieb = /\bMeisterbetrieb\b|\bMeisterfachbetrieb\b|\bMeister-?\s?Fachbetrieb\b/i.test(t);
  const titel = /\b([A-ZÄÖÜ][a-zäöüß-]*meister(?:in)?)\b/.exec(t)?.[1];
  const titelOk = titel && !/^(Bürgermeister|Hausmeister|Weltmeister|Meister)$/i.test(titel) ? titel : undefined;
  return { meisterbetrieb: betrieb || !!titelOk, meisterTitel: titelOk };
}

export function impressumFakten(text) {
  if (!text) return {};
  const ustId = /\bDE\s?(\d{3}\s?\d{3}\s?\d{3})\b/.exec(text)?.[0]?.replace(/\s/g, '');
  const register = /\b(HR[AB])\s*[-:.]?\s*(?:Nr\.?\s*)?(\d{2,7})\s*([A-Z]{1,2}\b)?/.exec(text);
  const gericht = /\b(Amtsgericht|Registergericht\s*:?\s*Amtsgericht)\s+([A-ZÄÖÜ][\wäöüß-]+(?:\s+(?:im|am|an der|in der)\s+[A-ZÄÖÜ][\wäöüß-]+)?)/.exec(text);
  const hwk = /\b(Handwerkskammer\s+(?:für\s+)?[A-ZÄÖÜ][\wäöüß-]+(?:[ -](?:[A-ZÄÖÜ][\wäöüß-]+|am|an der|im))*)/.exec(text)?.[1];
  const rolle = (/Handwerksrolle[^\n\d]{0,40}?(\d[\d /.-]{2,20}\d)/i.exec(text) ?? (hwk ? /(?:Betriebsnummer|Betriebs-Nr\.?|Mitgliedsnummer)\s*:?\s*(\d[\d /.-]{2,20}\d)/i.exec(text) : null))?.[1]?.replace(/\s+/g, ' ');
  // Anschrift der Kammer nur übernehmen, wenn sie eindeutig wie eine Adresse aussieht (Straße Nr., PLZ Ort)
  const kammerAdr = hwk
    ? new RegExp(`${hwk.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}[ ,]*\\n?\\s*([A-ZÄÖÜ][\\wäöüß. -]{2,40}\\s\\d{1,4}[a-z]?,?[ \\n]+\\d{5} [A-ZÄÖÜ][\\wäöüß-]+)`).exec(text)?.[1]?.replace(/\s*\n\s*/g, ', ')
    : undefined;
  return {
    ustId,
    registernummer: register ? `${register[1]} ${register[2]}${register[3] ? ` ${register[3]}` : ''}` : undefined,
    registergericht: gericht ? `Amtsgericht ${gericht[2]}` : undefined,
    handwerkskammer: hwk ? hwk.trim().slice(0, 80) : undefined,
    handwerkskammerAdresse: kammerAdr?.trim().slice(0, 120),
    handwerksrolleNr: rolle?.trim().slice(0, 40),
  };
}

/** Alles zusammen: Fakten aus Startseite, Impressum, Über-uns-Seite */
export function extrahiere({ start = '', impressum = '', ueberUns = '' } = {}) {
  const meister = meisterAus(start, impressum, ueberUns);
  return {
    inhaber: inhaberAus(impressum),
    email: emailAus(impressum) ?? emailAus(start),
    telefon: telefonAus(impressum) ?? telefonAus(start),
    gruendungsjahr: gruendungsjahrAus(start, ueberUns, impressum),
    rechtsform: rechtsformAus(impressum),
    ...meister,
    ...impressumFakten(impressum),
  };
}

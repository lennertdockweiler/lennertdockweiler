// Baut aus Lead + Website-Check eine site.config.json für das handwerker-template.
// Grundsatz: nichts erfinden. Unbekannte Fakten (Meisterbetrieb, Notdienst, Gründungsjahr,
// Bewertungen, Mitarbeiterzahl) werden weggelassen und Preset-Texte entsprechend entschärft.
import { kurznameAus, rechtsformAus } from './extraktion.mjs';
import { parseOeffnungszeiten } from './oeffnungszeiten.mjs';
import { normTelefon } from './util.mjs';

export const PALETTEN = {
  elektro: [{ primaer: '#1F2933', akzent: '#F5B700' }, { primaer: '#0B3D91', akzent: '#FFB000' }, { primaer: '#14213D', akzent: '#2EC4B6' }],
  shk: [{ primaer: '#0A3D62', akzent: '#38ADA9' }, { primaer: '#123C69', akzent: '#E85A4F' }, { primaer: '#1B4965', akzent: '#62B6CB' }],
  dachdecker: [{ primaer: '#3A2E39', akzent: '#C1121F' }, { primaer: '#2B2D42', akzent: '#D17A22' }, { primaer: '#283044', akzent: '#78A1BB' }],
  zimmerei: [{ primaer: '#3E2C1C', akzent: '#C08B5C' }, { primaer: '#2F3E46', akzent: '#CA6702' }],
  tischler: [{ primaer: '#4A3B2C', akzent: '#B5835A' }, { primaer: '#2F3E46', akzent: '#C9A227' }, { primaer: '#3D405B', akzent: '#E07A5F' }],
  maler: [{ primaer: '#2D3047', akzent: '#E84855' }, { primaer: '#1D3557', akzent: '#F4A261' }, { primaer: '#264653', akzent: '#E9C46A' }],
  fliesen: [{ primaer: '#22333B', akzent: '#5E9EA0' }, { primaer: '#2B2D42', akzent: '#8D99AE' }],
  metallbau: [{ primaer: '#1C1C1C', akzent: '#E4572E' }, { primaer: '#2E3440', akzent: '#88C0D0' }],
  galabau: [{ primaer: '#1B4332', akzent: '#95D5B2' }, { primaer: '#283618', akzent: '#DDA15E' }],
  bau: [{ primaer: '#2B2D42', akzent: '#F77F00' }, { primaer: '#212529', akzent: '#FFC300' }],
  allgemein: [{ primaer: '#2B3036', akzent: '#E2A400' }, { primaer: '#1E3A5F', akzent: '#F28C28' }],
};

const STILE = {
  elektro: ['modern-praezise', 'kraftvoll-bold'],
  shk: ['modern-praezise', 'kraftvoll-bold'],
  metallbau: ['modern-praezise', 'kraftvoll-bold'],
  tischler: ['manufaktur-warm', 'modern-praezise'],
  zimmerei: ['manufaktur-warm', 'kraftvoll-bold'],
  maler: ['manufaktur-warm', 'kraftvoll-bold', 'modern-praezise'],
  fliesen: ['manufaktur-warm', 'modern-praezise'],
  dachdecker: ['kraftvoll-bold', 'modern-praezise'],
  galabau: ['manufaktur-warm', 'kraftvoll-bold'],
  bau: ['kraftvoll-bold', 'modern-praezise'],
  allgemein: ['modern-praezise', 'manufaktur-warm', 'kraftvoll-bold'],
};

const SCHRIFT_ALTERNATIVEN = {
  'modern-praezise': { headline: 'manrope', text: 'hanken' },
  'manufaktur-warm': { headline: 'fraunces', text: 'hanken' },
  'kraftvoll-bold': { headline: 'bricolage', text: 'manrope' },
};

/** Neutrale Berufsbezeichnung fürs Impressum, wenn kein Meistertitel bekannt ist */
const BERUF = {
  elektro: 'Elektroniker',
  shk: 'Anlagenmechaniker für Sanitär-, Heizungs- und Klimatechnik',
  dachdecker: 'Dachdecker',
  zimmerei: 'Zimmerer',
  maler: 'Maler und Lackierer',
  tischler: 'Tischler',
  fliesen: 'Fliesen-, Platten- und Mosaikleger',
  metallbau: 'Metallbauer',
  galabau: 'Gärtner (Garten- und Landschaftsbau)',
  bau: 'Maurer',
};

const kuerze = (s, max) => (s.length <= max ? s : s.slice(0, max - 1).replace(/\s+\S*$/, '') + '…');

/** Preset-Sprachbausteine an bekannte Fakten anpassen (Meister, Notdienst, Familienbetrieb) */
export function ehrlicheTexte(info, gewerk, fakten) {
  const preset = info.presets[gewerk];
  const alle = { ...info.basisTexte, ...(preset.texte ?? {}) };
  const out = {};
  for (const [k, original] of Object.entries(alle)) {
    let v = original;
    if (!fakten.meisterbetrieb) {
      v = v
        .replace(/\{\{Ihr\|dein\}\} Meisterbetrieb/g, `{{Ihr|dein}} ${preset.betriebsart}`)
        .replace(/ aus Meisterhand/g, ' aus einer Hand')
        .replace(/ vom Meisterbetrieb in \{ort\}/g, ' aus {ort}')
        .replace(/Meisterbetrieb seit \{gruendungsjahr\}\.\s*/g, '')
        .replace(/(\p{L}+)-Meisterbetrieb/gu, '$1-Betrieb')
        .replace(/(\p{L}+)meisterbetrieb/gu, '$1betrieb')
        .replace(/\bMeisterbetrieb\b/g, preset.betriebsart);
    }
    if (!fakten.notdienst) {
      v = v
        .replace(/ – mit (?:Sturmschaden-)?Notdienst(?: rund um die Uhr)?/g, '')
        .replace(/,? (?:und )?(?:24h-|Sturmschaden-)Notdienst/g, '')
        .replace(/,? Notfälle sofort über unseren Notdienst/g, '')
        .replace(/Cool im Notfall\./g, 'Cool im Sommer.');
      // Was dann noch einen Notdienst verspricht, fällt auf den neutralen Basistext zurück
      if (/Notdienst|Notfall|rund um die Uhr/i.test(v) && k !== 'notdienstTitel' && k !== 'notdienstText') {
        v = (info.basisTexte[k] ?? '').replace(/\s*Seit \{gruendungsjahr\}\.?/g, '');
      }
    }
    if (k === 'ueberUnsTitel' && /Familienbetrieb|Generation/.test(v)) v = 'Über {kurzname}';
    v = v.replace(/\s{2,}/g, ' ').replace(/\s+([.,])/g, '$1').trim();
    if (v !== original) out[k] = v;
  }
  return out;
}

/** FAQ und Werte ohne Notdienst-Aussagen (nur zurückgeben, wenn sich etwas ändert) */
function ohneNotdienst(liste, felder) {
  const neu = liste
    .filter((e) => !/Notdienst|Notfall|rund um die Uhr/.test(e[felder[0]]))
    .map((e) => ({ ...e, [felder[1]]: e[felder[1]].replace(/,? Notfälle sofort über unseren Notdienst/g, '').replace(/,? (?:auch )?im Notdienst/g, '') }))
    .filter((e) => !/Notdienst|Notfall|rund um die Uhr/.test(e[felder[1]]));
  return JSON.stringify(neu) === JSON.stringify(liste) ? undefined : neu;
}

/**
 * @param lead      Lead inkl. pruefung/bewertung
 * @param info      Template-Infos (template-dump)
 * @param opts      { index, laufId, agentur, region, radiusKm, gebiet }
 */
export function baueVariante(lead, info, opts) {
  const p = lead.pruefung ?? {};
  const x = p.extrakt ?? {};
  const preset = info.presets[lead.gewerk] ?? info.presets.allgemein;
  const gewerk = info.presets[lead.gewerk] ? lead.gewerk : 'allgemein';
  const i = opts.index ?? 0;

  const kurzname = kurznameAus(lead.name);
  const rechtsform = rechtsformAus(lead.name) ?? x.rechtsform;
  const gewerkName = lead.gewerkBezeichnung ?? preset.bezeichnung;
  const ort = lead.adresse.ort;
  const meisterbetrieb = !!(x.meisterbetrieb && x.handwerkskammer && x.handwerksrolleNr);
  const gruendungsjahr = lead.gruendungsjahr ?? x.gruendungsjahr;
  const kannOhneJahr = info.gruendungsjahrOptional;
  const fakten = { meisterbetrieb, notdienst: false, gruendungsjahr };

  const oz = parseOeffnungszeiten(lead.oeffnungszeitenRoh);
  const oeffnungszeiten = oz
    ? { regulaer: oz.regulaer, sonder: [], ...(oz.hinweis ? { hinweis: oz.hinweis } : { hinweis: 'Termine auch nach Vereinbarung.' }) }
    : {
        regulaer: [
          { tage: ['mo', 'di', 'mi', 'do'], von: '07:30', bis: '17:00' },
          { tage: ['fr'], von: '07:30', bis: '13:00' },
        ],
        sonder: [],
        hinweis: 'Termine auch nach Vereinbarung.',
      };

  const palette = p.farben?.primaer ? p.farben : PALETTEN[gewerk][i % PALETTEN[gewerk].length];
  const stile = STILE[gewerk] ?? STILE.allgemein;
  const stilPreset = stile[i % stile.length];
  const radiusKm = opts.radiusKm ?? 25;

  const telefon = lead.telefon ?? normTelefon(x.telefon) ?? '+49 000 000000';
  const email = lead.email ?? x.email ?? 'kontakt@example.com';
  const inhaber = x.inhaber ?? lead.operator;

  const leistungen = preset.leistungen.filter((l) => l.slug !== 'notdienst').map((l) => ({ slug: l.slug }));
  const faq = ohneNotdienst(preset.faq, ['frage', 'antwort']);
  const werte = ohneNotdienst(preset.werte, ['titel', 'text']);
  const texte = ehrlicheTexte(info, gewerk, fakten);

  const gebiet = opts.gebiet?.orte?.length
    ? opts.gebiet
    : { orte: [{ name: ort, lat: lead.geo.lat, lng: lead.geo.lng, plz: [lead.adresse.plz] }], plz: [lead.adresse.plz], plzAufAnfrage: [] };

  const sektionLayouts = {
    // Bento zeigt große Fotoflächen – ohne echte Fotos wirken Tabs und Liste hochwertiger
    leistungen: ['tabs', 'liste'][i % 2],
    ablauf: ['liste', 'gepinnt'][i % 2],
    faq: ['akkordeon', 'zweispaltig'][i % 2],
  };
  const toene = [
    ['flaeche', 'hell', 'dunkel', 'flaeche'],
    ['hell', 'flaeche', 'marke', 'hell'],
    ['flaeche', 'dunkel', 'hell', 'flaeche'],
  ][i % 3];

  const agentur = opts.agentur ?? {};
  const bannerText = kuerze(`Unverbindlicher Entwurf von ${agentur.name ?? 'uns'} für ${kurzname} – Inhalte teils beispielhaft.`, 120);

  const config = {
    $schema: '../_schema.json',
    '//fabrik': {
      lauf: opts.laufId,
      erzeugt: new Date().toISOString().slice(0, 10),
      quelle: 'OpenStreetMap (ODbL) + öffentliche Website',
      osm: lead.id,
      hinweis: 'Automatisch erzeugt von der Vorschau-Fabrik. Unbekannte Fakten wurden bewusst weggelassen.',
    },
    meta: { slug: lead.slug, anrede: 'sie', noindex: true },
    betrieb: {
      name: kuerze(lead.name, 80),
      kurzname,
      ...(rechtsform ? { rechtsform } : {}),
      inhaber: inhaber ?? kurzname,
      slogan: kuerze(`${gewerkName} für ${ort} und ${opts.region ? opts.region.replace(/^(am|im|an der|in der)\s+/, '') : 'Umgebung'}`, 90),
      ...(gruendungsjahr || !kannOhneJahr ? { gruendungsjahr: gruendungsjahr ?? new Date().getFullYear() } : {}),
      adresse: {
        strasse: kuerze(lead.adresse.strasse, 60),
        plz: lead.adresse.plz,
        ort,
        ...(opts.region ? { region: opts.region } : {}),
      },
      geo: lead.geo,
      telefon,
      email,
      oeffnungszeiten,
      socialLinks: lead.socialLinks ?? [],
    },
    branding: {
      farben: { primaer: palette.primaer, ...(palette.akzent ? { akzent: palette.akzent } : {}) },
      stilPreset,
      ...(i % 2 === 1 ? { schriftPaar: SCHRIFT_ALTERNATIVEN[stilPreset] } : {}),
      radius: ['dezent', 'rund', 'eckig'][i % 3],
      animationsIntensitaet: 'standard',
      bildstil: { grain: true, toenung: 0.1 },
    },
    gewerk,
    ...(lead.gewerkBezeichnung ? { gewerkBezeichnung: lead.gewerkBezeichnung } : {}),
    meisterbetrieb,
    ...(meisterbetrieb
      ? {
          ...(x.meisterTitel && inhaber ? { meisterName: inhaber } : {}),
          handwerkskammer: { name: x.handwerkskammer, adresse: x.handwerkskammerAdresse ?? x.handwerkskammer },
          handwerksrolleNr: x.handwerksrolleNr,
        }
      : {}),
    notdienst: { aktiv: false },
    einsatzgebiet: {
      zentrum: { name: ort, lat: lead.geo.lat, lng: lead.geo.lng },
      radiusKm,
      orte: gebiet.orte,
      plz: gebiet.plz,
      plzAufAnfrage: gebiet.plzAufAnfrage,
    },
    leistungen,
    ...(faq ? { faq } : {}),
    ...(werte ? { werte } : {}),
    texte,
    sektionen: [
      { typ: 'hero', layout: 'typo' },
      { typ: 'leistungen', layout: sektionLayouts.leistungen, id: 'leistungen', ton: toene[0] },
      { typ: 'ablauf', layout: sektionLayouts.ablauf, ton: toene[1] },
      { typ: 'einsatzgebiet', layout: 'karte', ton: toene[2] === 'marke' ? 'hell' : toene[2] },
      { typ: 'faq', layout: sektionLayouts.faq },
      { typ: 'cta', layout: 'kontakt', ton: toene[3] },
    ],
    seiten: { leistungen: true, referenzen: false, ueberUns: false, karriere: false, notdienst: false, kontakt: true },
    seo: { titel: kuerze(`${kurzname} – ${gewerkName} in ${ort}`, 65) },
    rechtliches: {
      berufsbezeichnung: x.meisterTitel ?? BERUF[gewerk] ?? gewerkName,
      verleihungsstaat: 'Deutschland',
      vertretungsberechtigt: [inhaber ?? 'Angaben folgen'],
      ...(x.registergericht ? { registergericht: x.registergericht } : {}),
      ...(x.registernummer ? { registernummer: x.registernummer } : {}),
      ...(x.ustId ? { ustId: x.ustId } : {}),
    },
    integrationen: { formularEndpoint: '', karte: { aktiv: false }, analytics: { aktiv: false } },
    demo: {
      banner: { aktiv: true, text: bannerText },
      agentur: {
        name: agentur.name ?? 'Agentur',
        ...(normTelefon(agentur.telefon) ? { telefon: normTelefon(agentur.telefon) } : {}),
        ...(agentur.email ? { email: agentur.email } : {}),
        ...(agentur.website ? { website: agentur.website } : {}),
      },
      pitchSeite: true,
    },
  };

  const luecken = [];
  if (telefon.includes('000000')) luecken.push('Telefonnummer fehlt');
  if (email.endsWith('@example.com')) luecken.push('E-Mail fehlt');
  if (!oz) luecken.push(lead.oeffnungszeitenRoh ? 'Öffnungszeiten nicht lesbar – Standardwerte' : 'Öffnungszeiten unbekannt – Standardwerte');
  if (!inhaber) luecken.push('Inhaber unbekannt');
  if (!gruendungsjahr && !kannOhneJahr) luecken.push('Gründungsjahr unbekannt – Template braucht ein Jahr (Template-Update einspielen)');
  if (x.meisterbetrieb && !meisterbetrieb) luecken.push('Meisterbetrieb laut Website – HWK/Handwerksrolle ergänzen');
  return { config, luecken };
}

/** Kurzer Text für CREDITS.md der Variante (wird im Impressum der Vorschau genannt) */
export const creditsText = () =>
  `# Bildnachweise und Quellen\n\n- Keine Fotos verwendet: Alle Bildflächen sind Platzhalter.\n- Betriebsdaten und Koordinaten: © OpenStreetMap-Mitwirkende, Lizenz ODbL (openstreetmap.org/copyright).\n- Orte und Postleitzahlen des Einsatzgebiets: GeoNames (geonames.org), Lizenz CC BY 4.0.\n`;

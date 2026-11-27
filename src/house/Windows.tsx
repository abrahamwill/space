/**
 * The window that opens over a zoomed room. Copy comes from the same data as the fast view;
 * anything not written yet stays a [bracket] placeholder.
 */
import { useState } from 'react';
import type { HouseContent } from './content';

/**
 * The project's picture: a plain rounded screenshot (the window around it is chrome enough), or a soft
 * tile when there isn't one yet.
 */
function Thumb({ title, src, position }: { title: string; src?: string; position?: string }) {
  return (
    <div className="hx-thumb" aria-hidden="true">
      {src ? <img src={src} alt="" style={{ objectPosition: position }} /> : <div className="hx-thumb-empty">{title}</div>}
    </div>
  );
}

/** A window's heading: an optional small label above the title, kept with it, and an optional line under. */
function Head({ label, title, sub }: { label?: React.ReactNode; title: React.ReactNode; sub?: React.ReactNode }) {
  return (
    <header className="hx-head">
      {label && <span className="hx-eyebrow">{label}</span>}
      <h3 className="hx-h">{title}</h3>
      {sub && <span className="hx-sub">{sub}</span>}
    </header>
  );
}

function Rows({ rows }: { rows: ReadonlyArray<{ what: string; when?: string }> }) {
  return (
    <ul className="hx-rows">
      {rows.map((r) => (
        <li key={r.what}>
          <span>{r.what}</span>
          {r.when && <span className="hx-muted">{r.when}</span>}
        </li>
      ))}
    </ul>
  );
}

/** Instax-style prints (the running wall, the bedroom photo wall). */
function Instax({ photos, label }: { photos: ReadonlyArray<{ src?: string; caption: string }>; label: string }) {
  return (
    <ul className="hx-instax" aria-label={label}>
      {photos.map((ph, i) => (
        <li key={i}>
          {ph.src ? <img src={ph.src} alt={ph.caption} loading="lazy" /> : <span className="hx-instax-empty" aria-hidden="true" />}
          <span>{ph.caption}</span>
        </li>
      ))}
    </ul>
  );
}

function Ph({ children, ratio = '16 / 9' }: { children: string; ratio?: string }) {
  return (
    <div className="hx-ph" style={{ aspectRatio: ratio }} role="img" aria-label={children}>
      <span>{children}</span>
    </div>
  );
}

function Folders({ content }: { content: HouseContent }) {
  const [i, setI] = useState(0);
  const w = content.featured[i];
  if (!w) return null;
  return (
    <>
      <div className="hx-tabs" role="tablist" aria-label="Featured folders">
        {content.featured.map((f, k) => (
          <button key={f.slug} type="button" role="tab" aria-selected={k === i} onClick={() => setI(k)}>
            {f.short ?? f.company}
          </button>
        ))}
      </div>
      <div className="hx-folder" role="tabpanel">
        <Thumb title={w.short ?? w.company} src={w.thumb} position={w.thumbPosition} />
        <Head label={`${w.company} · ${w.role} · ${w.year}`} title={w.published ? w.title : w.summary} />
        {w.published && <p>{w.tldr ?? w.summary}</p>}
        {w.published && w.metrics.length > 0 && (
          <ul className="hx-metrics">
            {w.metrics.map((m, k) => (
              <li key={k}><strong>{m.value}</strong><span>{m.label}</span></li>
            ))}
          </ul>
        )}
        <div className="hx-actions">
          {w.published ? (
            <a className="hx-btn" href={`/work/${w.slug}`}>Read the full case study</a>
          ) : (
            <span className="hx-muted">[Case study in progress]</span>
          )}
          {w.prototypeUrl && <a href={w.prototypeUrl}>Play the prototype</a>}
        </div>
      </div>
    </>
  );
}

function LabItem({ content, index, extra }: { content: HouseContent; index: number; extra?: React.ReactNode }) {
  const item = content.lab[index];
  return (
    <>
      <Head label={item.status} title={item.title} />
      <p>{item.body}</p>
      {extra}
    </>
  );
}

export const WINDOW_TITLES: Record<string, string> = {
  folders: 'Studio · featured work',
  archive: 'Studio · archive',
  pinboard: 'Studio · how I work',
  prototypehub: 'Lab · workbench',
  arcade: 'Lab · arcade',
  voice: 'Lab · voice gadget',
  whiteboard: 'Lab · whiteboard',
  window: 'Main room · about me',
  turntable: 'Main room · turntable',
  notice: 'Main room · talks & workshops',
  door: 'Main room · front door',
  photos: 'Main room · record shelf',
};

export interface Deck {
  /** The record asked for (instant). */
  record: number;
  state: 'playing' | 'coming' | 'swapping';
  pick: (i: number) => void;
}

function Turntable({ content, deck }: { content: HouseContent; deck: Deck }) {
  const r = content.records[deck.record];
  if (!r) return null;
  return (
    <>
      <Head label={deck.state === 'playing' ? 'On the turntable' : 'Changing the record…'} title={r.title} sub={r.artist} />
      <ul className="hx-records" aria-label="Records">
        {content.records.map((rec, i) => (
          <li key={i}>
            <button type="button" aria-pressed={i === deck.record} onClick={() => deck.pick(i)}>
              <span className="hx-record-dot" style={{ background: rec.label }} aria-hidden="true" />
              <span>{rec.title}</span>
              <span className="hx-muted">{rec.artist}</span>
            </button>
          </li>
        ))}
      </ul>
    </>
  );
}

export function WindowBody({ id, content, deck }: { id: string; content: HouseContent; deck: Deck }) {
  const { site, about } = content;
  switch (id) {
    case 'folders':
      return <Folders content={content} />;
    case 'archive':
      return (
        <>
          <Head title="The whole shelf" />
          <p>[Older and smaller projects, one line each, outcome first.]</p>
          <Rows rows={[{ what: '[Project]', when: '[Year]' }, { what: '[Project]', when: '[Year]' }, { what: '[Project]', when: '[Year]' }]} />
        </>
      );
    case 'pinboard':
      return (
        <>
          <Head title="How I work" />
          <p>[Three or four principles, one line each, with a small example for each.]</p>
        </>
      );
    case 'prototypehub':
      return (
        <LabItem
          content={content}
          index={0}
          extra={
            <>
              <ul className="hx-chips">
                {['Comments', 'Touch hints', 'Guided flows', 'Versioning', 'Present mode'].map((c) => <li key={c}>{c}</li>)}
              </ul>
              <Thumb title="Prototype Hub" src="/images/lab/prototype-hub-cover.webp" position="top left" />
              <div className="hx-actions">
                <a className="hx-btn" href="/work/prototype-hub">Read the case study</a>
              </div>
            </>
          }
        />
      );
    case 'arcade':
      return <LabItem content={content} index={1} extra={<Thumb title="Pet game" src="/images/lab/pet-game-cover.webp" />} />;
    case 'voice':
      return <LabItem content={content} index={2} />;
    case 'whiteboard':
      return (
        <>
          <Head title="Learning notes" />
          <p>[What I'm learning right now, and the notes I keep while I do.]</p>
        </>
      );
    case 'window':
      return (
        <>
          <Head title="And this is where I live, off the clock." />
          <p>{about.body}</p>
          <Rows rows={about.facts} />
        </>
      );
    case 'turntable':
      return <Turntable content={content} deck={deck} />;
    case 'notice':
      return (
        <>
          <Head title="Talks and workshops" />
          <Rows
            rows={[
              { what: 'Workshops at RISTEK and COMPFEST', when: 'Speaker' },
              { what: 'Digital Product Design SIG, RISTEK', when: 'Deputy' },
              { what: 'Gen AI Labs community' },
            ]}
          />
        </>
      );
    case 'door':
      return (
        <>
          <Head title="The door's open." />
          <p>If any of this sounds like your kind of problem, come say hi.</p>
          <ul className="hx-links">
            <li><a href={site.emailHref}>{site.email}</a></li>
            <li><a href={site.linkedin}>LinkedIn</a></li>
            <li><a href={site.cv}>CV (PDF)</a></li>
          </ul>
        </>
      );
    // House v2 (Pinwheel): what these open is still an open question (design/house-v2-blender.md)
    case 'running':
      return (
        <>
          <Head title="Miles on the wall" />
          <p>{content.running.intro}</p>
          <Instax photos={content.running.photos} label="Photos from my running" />
          <Rows rows={content.running.medals} />
        </>
      );
    case 'photowall':
      return (
        <>
          <Head title="Places I've been" />
          <p>{content.travel.intro}</p>
          <Instax photos={content.travel.photos} label="Travel photos" />
        </>
      );
    case 'photos':
      return (
        <>
          <Head title="Off the record" />
          <Ph ratio="16 / 10">[Photos]</Ph>
        </>
      );
    default:
      return null;
  }
}

/**
 * The window that opens over a zoomed room. Copy comes from the same data as the fast view;
 * anything not written yet stays a [bracket] placeholder.
 */
import { useState } from 'react';
import type { HouseContent } from './content';

function Cover({ variant, label }: { variant: 'sun' | 'moon' | 'mast'; label: string }) {
  const bg = { sun: 'var(--mustard)', moon: 'var(--cobalt)', mast: 'var(--red)' }[variant];
  return (
    <div className="hx-cover" style={{ background: bg }} aria-hidden="true">
      <svg viewBox="0 0 100 100" preserveAspectRatio="none">
        {variant === 'sun' && (
          <>
            <circle cx="39" cy="39" r="29" fill="var(--red)" />
            <rect x="0" y="77" width="100" height="9" fill="var(--ink)" />
            <circle cx="77" cy="57" r="13" fill="var(--cobalt)" />
          </>
        )}
        {variant === 'moon' && (
          <>
            <circle cx="50" cy="44" r="28" fill="var(--mustard)" />
            <path d="M50 16 A28 28 0 0 1 50 72 Z" fill="var(--page)" />
          </>
        )}
        {variant === 'mast' && (
          <>
            <circle cx="80" cy="20" r="40" fill="var(--page)" />
            <rect x="10" y="0" width="9" height="100" fill="var(--ink)" />
            <rect x="30" y="52" width="30" height="30" fill="var(--mustard)" />
          </>
        )}
      </svg>
      <span className="hx-cover-label" style={{ left: variant === 'mast' ? '24%' : '6%' }}>{label}</span>
    </div>
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
  const n = String(i + 1).padStart(2, '0');
  return (
    <>
      <div className="hx-tabs" role="tablist" aria-label="Featured folders">
        {content.featured.map((f, k) => (
          <button key={f.slug} type="button" role="tab" aria-selected={k === i} onClick={() => setI(k)}>
            {String(k + 1).padStart(2, '0')}
          </button>
        ))}
      </div>
      <div className="hx-folder" role="tabpanel">
        <Cover variant={w.cover} label={`Studio ${n}`} />
        <span className="hx-muted hx-small">{w.company} · {w.role} · {w.year}</span>
        <h3 className="hx-h">{w.published ? w.title : w.summary}</h3>
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
            <a className="btn" href={`/work/${w.slug}`}>Read the full case study</a>
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
      <span className="hx-muted hx-small">{item.status}</span>
      <h3 className="hx-h">{item.title}</h3>
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
      <span className="hx-muted hx-small">{deck.state === 'playing' ? 'On the turntable' : 'Changing the record…'}</span>
      <h3 className="hx-h">{r.title}</h3>
      <p>{r.artist}</p>
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
          <h3 className="hx-h">The whole shelf</h3>
          <p>[Older and smaller projects, one line each, outcome first.]</p>
          <Rows rows={[{ what: '[Project]', when: '[Year]' }, { what: '[Project]', when: '[Year]' }, { what: '[Project]', when: '[Year]' }]} />
        </>
      );
    case 'pinboard':
      return (
        <>
          <h3 className="hx-h">How I work</h3>
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
              <Ph>[Screenshot: check internal prototype names before publishing]</Ph>
            </>
          }
        />
      );
    case 'arcade':
      return <LabItem content={content} index={1} extra={<Ph>[Screenshot of the pet game]</Ph>} />;
    case 'voice':
      return <LabItem content={content} index={2} />;
    case 'whiteboard':
      return (
        <>
          <h3 className="hx-h">Learning notes</h3>
          <p>[What I'm learning right now, and the notes I keep while I do.]</p>
        </>
      );
    case 'window':
      return (
        <>
          <h3 className="hx-h">And this is where I live, off the clock.</h3>
          <p>{about.body}</p>
          <Rows rows={about.facts} />
        </>
      );
    case 'turntable':
      return <Turntable content={content} deck={deck} />;
    case 'notice':
      return (
        <>
          <h3 className="hx-h">Talks and workshops</h3>
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
          <h3 className="hx-h">The door's open.</h3>
          <p>If any of this sounds like your kind of problem, come say hi.</p>
          <ul className="hx-links">
            <li><a href={site.emailHref}>{site.email}</a></li>
            <li><a href={site.linkedin}>LinkedIn</a></li>
            <li><a href={site.cv}>CV (PDF)</a></li>
          </ul>
        </>
      );
    case 'photos':
      return (
        <>
          <h3 className="hx-h">Off the record</h3>
          <Ph ratio="4 / 3">[Photos]</Ph>
        </>
      );
    default:
      return null;
  }
}

// Everything the owner fills in lives here or in src/content/work/*.mdx.
// Values in [brackets] are placeholders. Never replace them with guessed facts or metrics.

export const site = {
  name: '[Your name]',
  role: 'Senior Product Designer, Gokomodo',
  description:
    'Senior product designer. I design practical tools for farmers and field teams, and prototype them in code.',
  email: '[email]',
  emailHref: '#', // TODO(owner): 'mailto:you@example.com'
  linkedin: '#', // TODO(owner): LinkedIn URL
  cv: '#', // TODO(owner): put the PDF in /public and link it, e.g. '/cv.pdf'
  year: '[Year]',
};

/** Where "Step inside" goes. Milestone 2 replaces the page with the 3D house. */
export const houseHref = '/house';

export const lab = [
  {
    title: 'Prototype Hub',
    body: 'A home for coded prototypes, so handoff has comments, touch hints, guided flows and versions in one place.',
    status: 'In use by my team',
    mark: 'circle',
  },
  {
    title: 'A cozy pet game',
    body: "Feed, bathe, decorate. It's where I practise game feel and the small loops that make people come back.",
    status: 'In development',
    mark: 'square',
  },
  {
    title: 'Conversational AI',
    body: "Learning to design for voice and chat, bit by bit, for people who'd rather talk than type.",
    status: 'Learning',
    mark: 'triangle',
  },
] as const;

/**
 * The records by the turntable in the house. Placeholders until the owner picks real ones.
 * `label` is the record's label colour on the platter. Add `src` (an audio file in /public, e.g.
 * '/music/track.mp3') to let visitors turn the sound on; with no `src` anywhere the sound button is hidden.
 */
export const records: Array<{ title: string; artist: string; label: string; src?: string }> = [
  { title: '[Track title 1]', artist: '[Artist]', label: '#c8442b' },
  { title: '[Track title 2]', artist: '[Artist]', label: '#2b4fa8' },
  { title: '[Track title 3]', artist: '[Artist]', label: '#e0a72e' },
  { title: '[Track title 4]', artist: '[Artist]', label: '#fbf3e6' },
];

export const about = {
  body: "I studied computer science at Universitas Indonesia, then fell for the part where software meets people. Since 2021 I've designed for farmers and field teams at Gokomodo. Most evenings there's a record on, a game half-built, or a workshop to prep.",
  facts: [
    { what: 'Senior Product Designer, Gokomodo', when: '2021 – now' },
    { what: 'Workshops at RISTEK and COMPFEST', when: 'Speaker' },
    { what: 'BSc Computer Science, Universitas Indonesia', when: '2021' },
  ],
};

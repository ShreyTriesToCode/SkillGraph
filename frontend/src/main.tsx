import React, { Suspense, lazy, useEffect, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { ArrowUpRight, ArrowRight, Network, UserRound, BriefcaseBusiness, ChartNoAxesCombined, Route, FlaskConical, Check, Plus, BookOpen, Download, ChevronRight, Menu } from 'lucide-react';
import Overview from './Overview';
const GraphView = lazy(() => import('./GraphView'));
const ScoreChart = lazy(() => import('./ScoreChart'));
import './style.css';
type Skill = {
    id: string;
    label: string;
    source: string;
    aliases: string[];
    category: string;
};
type Student = {
    id: number;
    name: string;
    course: string;
    year: number;
    skills: Record<string, number>;
    interests: string[];
    projects: string;
    demo: boolean;
};
type Requirement = {
    skill: string;
    label: string;
    type: string;
    proficiency?: number;
};
type Career = {
    id: string;
    label: string;
    score: number;
    coverage: number;
    description: string;
    source: string;
    matching: Requirement[];
    missing_essential: Requirement[];
    optional: Requirement[];
    components: Record<string, number>;
    contributions: Record<string, number>;
    explanation: string;
    semantic_evidence: {
        required: string;
        related_known: string[];
        credit: number;
        source: string;
    }[];
};
type Step = {
    skill: string;
    label: string;
    stage: number;
    importance: string;
    prerequisites: string[];
    objective: string;
    practice: string;
    estimated_hours: number;
    completed: boolean;
};
const pages = ['Overview', 'Profile', 'Careers', 'Skill gaps', 'Knowledge graph', 'Learning roadmap'];
const legacyPages: Record<string,string> = {'Dashboard':'Overview','Faculty demo':'Overview','Model & data':'Knowledge graph'};
function resolvePage(value:string){const resolved=legacyPages[value]||value;return pages.includes(resolved)?resolved:'Overview'}
const icons = [BookOpen, UserRound, BriefcaseBusiness, ChartNoAxesCombined, Network, Route];
async function api<T = any>(path: string, options?: RequestInit): Promise<T> { const r = await fetch('/api' + path, options); if (!r.ok) {
    const e = await r.json().catch(() => ({ detail: r.statusText }));
    throw Error(typeof e.detail === 'string' ? e.detail : JSON.stringify(e.detail));
} return r.json(); }
const json = (body: unknown) => ({ headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
function App() {
    const [page, setPage] = useState(() => { try {
        const value = decodeURIComponent(location.hash.slice(1));
        return resolvePage(value);
    }
    catch {
        return 'Overview';
    } });
    const [students, setStudents] = useState<Student[]>([]);
    const [student, setStudent] = useState<Student | null>(null);
    const [skills, setSkills] = useState<Skill[]>([]);
    const [occupations, setOccupations] = useState<{
        id: string;
        label: string;
    }[]>([]);
    const [careers, setCareers] = useState<Career[]>([]);
    const [target, setTarget] = useState('data-engineer');
    const [steps, setSteps] = useState<Step[]>([]);
    const [graph, setGraph] = useState<any>(null);
    const [insights, setInsights] = useState<any>(null);
    const [error, setError] = useState('');
    const [busy, setBusy] = useState(false);
    const [skillInput, setSkillInput] = useState('');
    const [level, setLevel] = useState(3);
    const [filter, setFilter] = useState('');
    const [inspect, setInspect] = useState<any>(null);
    const [query, setQuery] = useState('');
    const [queryResult, setQueryResult] = useState<any>(null);
    const [draft, setDraft] = useState<Student | null>(null);
    const [acquired, setAcquired] = useState(false);
    const [file, setFile] = useState<File | null>(null);
    const [schema, setSchema] = useState<any>(null);
    const [mapping, setMapping] = useState<Record<string, string>>({});
    const [source, setSource] = useState('Local student CSV');
    const [importResult, setImportResult] = useState<any>(null);
    const [mobile, setMobile] = useState(false);
    const [compare, setCompare] = useState<string[]>([]);
    const refreshVersion = useRef(0);
    const desiredStudent = useRef<Student | null>(null);
    const desiredTarget = useRef(target);
    desiredTarget.current = target;
    const pendingWork = useRef(0);
    const profileUnsaved = !!draft && JSON.stringify(draft) !== JSON.stringify(student);
    const selected = careers.find(x => x.id === target);
    const label = (id: string) => skills.find(s => s.id === id)?.label || id;
    const go = (p: string) => { setPage(p); location.hash = p; setMobile(false); };
    async function run(fn: () => Promise<void>) { pendingWork.current++; setBusy(true); setError(''); try {
        await fn();
    }
    catch (e) {
        setError((e as Error).message);
    }
    finally {
        pendingWork.current--; setBusy(pendingWork.current > 0);
    } }
    async function refresh(s: Student) { const version = ++refreshVersion.current; desiredStudent.current = s; const requestTarget = desiredTarget.current; s = await api<Student>(`/students/${s.id}`); const [r, road, g, i] = await Promise.all([api(`/students/${s.id}/recommendations`), api(`/students/${s.id}/roadmap?occupation=${encodeURIComponent(requestTarget)}`), api(`/graph?sid=${s.id}&occupation=${encodeURIComponent(requestTarget)}`), api('/insights')]); if (version !== refreshVersion.current) return; setStudent(s); setDraft(s); setCareers(r.recommendations); setSteps(road); setGraph(g); setInsights(i); if (!query)
        setQuery(g.queries.shared); }
    useEffect(() => { run(async () => { const [c, ss] = await Promise.all([api('/catalog'), api<Student[]>('/students')]); setSkills(c.skills); setOccupations(c.occupations); setStudents(ss); if (ss.length)
        await refresh(ss.find(s => s.demo) || ss[0]); }); }, []);
    useEffect(() => { if (student)
        run(() => refresh(desiredStudent.current || student)); }, [target]);
    useEffect(() => { const navigate = () => { if(location.hash === '#main-content') return; let raw=''; try {raw=decodeURIComponent(location.hash.slice(1))}catch{}const next=resolvePage(raw);setPage(next);setMobile(false);if(raw!==next)history.replaceState(null,'','#'+encodeURIComponent(next)); }; const escape = (e: KeyboardEvent) => { if (e.key === 'Escape') {
        setMobile(false);
        document.querySelector<HTMLButtonElement>('.mobile-toggle')?.focus();
    } }; navigate();window.addEventListener('hashchange', navigate); window.addEventListener('keydown', escape); return () => { window.removeEventListener('hashchange', navigate); window.removeEventListener('keydown', escape); }; }, []);
    useEffect(() => { document.title = `${page} · SkillGraph`; }, [page]);
    async function save(s: Student) { const selectionAtSave = desiredStudent.current?.id; const updated = await api<Student>('/students' + (s.id ? '/' + s.id : ''), { method: s.id ? 'PUT' : 'POST', ...json({ name: s.name, course: s.course, year: s.year, skills: s.skills, interests: s.interests, projects: s.projects }) }); setStudents(await api('/students')); await refresh(desiredStudent.current && desiredStudent.current.id !== selectionAtSave ? desiredStudent.current : updated); }
    async function addSkill(id?: string) { const raw = id || skillInput; const found = skills.find(s => [s.id, s.label, ...s.aliases].some(v => v.toLowerCase() === raw.toLowerCase())); if (!found)
        throw Error('Choose a recognized skill from the suggestions.'); if (!student)
        return; await save({ ...student, skills: { ...student.skills, [found.id]: level } }); setSkillInput(''); }
    const addControl = <div className="inline"><label className="sr-only" htmlFor="skill">Skill</label><input id="skill" list="skill-list" placeholder="Add a skill, e.g. ETL" value={skillInput} onChange={e => setSkillInput(e.target.value)}/><datalist id="skill-list">{skills.map(s => <option key={s.id} value={s.label}/>)}</datalist><select aria-label="Self-reported proficiency" value={level} onChange={e => setLevel(+e.target.value)}>{[1, 2, 3, 4, 5].map(n => <option key={n} value={n}>{n}/5</option>)}</select><button disabled={busy || !student} onClick={() => run(() => addSkill())}><Plus size={16}/>Add skill</button></div>;
    const careerSelect = <label className="select-label">Target occupation<select aria-label="Target occupation" value={target} onChange={e => { setTarget(e.target.value); }}>{occupations.map(o => <option key={o.id} value={o.id}>{o.label}</option>)}</select></label>;
    const chart = (data: any[], height = 260, keys = ['score']) => <Suspense fallback={<div className="chart-loading">Loading comparison…</div>}><ScoreChart data={data} height={height} keys={keys}/></Suspense>;
    const tags = (xs: Requirement[], kind: string) => <div className="tags">{xs.length ? xs.map(s => <span key={s.skill} className={'tag ' + kind}>{kind === 'match' && <Check size={12}/>} {s.label}{s.proficiency && <small>{s.proficiency}/5</small>}</span>) : <span className="muted">None in this category</span>}</div>;
    return <div className="app"><a href="#main-content" className="skip-link">Skip to content</a>{mobile && <button className="nav-scrim" aria-label="Close navigation" onClick={() => setMobile(false)}/>}<aside className={mobile ? 'open' : ''} id="workspace-navigation"><a className="brand" href="#Overview" onClick={() => go('Overview')}><span className="brand-icon"><Network size={23}/></span>SkillGraph<span className="brand-dot">.</span></a><div className="workspace">Your workspace</div><nav aria-label="Main navigation">{pages.map((p, i) => { const Icon = icons[i]; return <button key={p} aria-label={p} aria-current={page === p ? 'page' : undefined} className={page === p ? 'nav-item active' : 'nav-item'} onClick={() => go(p)}><Icon size={18}/>{p}</button>; })}</nav><div className="sidebar-foot"><Network size={20}/><strong>Every match has a reason.</strong><p>Follow the skills, relationships, and evidence behind your results.</p><button className="text-button" onClick={() => go('Knowledge graph')}>See how it works <ArrowUpRight size={16}/></button></div></aside>
 <main id="main-content" tabIndex={-1}><header><button className="mobile-toggle secondary" onClick={() => setMobile(!mobile)} aria-expanded={mobile} aria-controls="workspace-navigation" aria-label="Toggle navigation"><Menu size={20}/></button><div className="breadcrumb">Workspace <ChevronRight size={14}/><strong>{page}</strong></div><span className="status"><span className="tiny-dot"/> {student?.demo ? 'Fictional profile' : 'Student profile'}</span><label className="student-switcher">Profile<select aria-label="Select student" value={student?.id || ''} onChange={e => run(async () => { const s = students.find(x => x.id === +e.target.value)!; await refresh(s); })}>{students.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}</select></label><div className="avatar">{student?.name.split(' ').map(x => x[0]).slice(-2).join('') || 'S'}</div></header>
 {error && <div className="error" role="alert">{error}<button className="secondary" onClick={() => setError('')}>Dismiss</button></div>}{busy && <div className="loading" role="status">Updating analysis…</div>}
 <div className="content">
 {page === 'Overview' ? <Overview student={student} career={selected} steps={steps} go={go}/> :
            <><div className="page-heading"><h1>{page}</h1><p>{({ 'Profile': 'Build a picture of what you know. Proficiency is self-reported.', 'Careers': 'Ranked by weighted coverage, semantic relationships, and learned similarity.', 'Skill gaps': 'See what you already bring and where to focus next.', 'Knowledge graph': 'Follow the evidence connecting students, skills, and occupations.', 'Learning roadmap': 'Turn missing skills into an ordered, practical learning plan.' } as Record<string, string>)[page] || 'A personalized view of your skills, career matches, and learning priorities.'}</p></div>
 {page === 'Profile' && draft && <div className="grid profile-grid"><section className="card"><div className="section-head"><h2>Student profile</h2><button className="secondary" onClick={() => setDraft({ id: 0, name: '', course: 'B.Tech CSE', year: 3, skills: {}, interests: [], projects: '', demo: false })}>New student</button></div><label>Name or anonymous identifier<input value={draft.name} onChange={e => setDraft({ ...draft, name: e.target.value })}/></label><div className="grid two"><label>Academic course<input value={draft.course} onChange={e => setDraft({ ...draft, course: e.target.value })}/></label><label>Academic year<input type="number" min={1} max={6} value={draft.year} onChange={e => setDraft({ ...draft, year: +e.target.value })}/></label></div><label>Career interests (comma separated)<input value={draft.interests.join(',')} onChange={e => setDraft({ ...draft, interests: e.target.value.split(',') })}/></label><label>Projects and experience<textarea value={draft.projects} onChange={e => setDraft({ ...draft, projects: e.target.value })}/></label><button disabled={busy || !draft.name.trim()} onClick={() => run(() => save(draft))}>Save profile <Check size={16}/></button></section><section className="card"><h2>Skills & proficiency</h2><p className="muted">{profileUnsaved ? 'Save your profile before editing skills.' : 'Skill changes save when you make them.'}</p>{draft.id === student?.id ? <fieldset className="skill-editor" disabled={busy || profileUnsaved}>{addControl}<div className="skill-list">{student && Object.entries(student.skills).map(([s, l]) => <div key={s}><strong>{label(s)}</strong><select aria-label={'Proficiency ' + label(s)} value={l} onChange={e => run(() => save({ ...student, skills: { ...student.skills, [s]: +e.target.value } }))}>{[1, 2, 3, 4, 5].map(n => <option key={n} value={n}>{n}/5</option>)}</select><button className="text-button" aria-label={'Remove ' + label(s)} onClick={() => run(async () => { const next = { ...student.skills }; delete next[s]; await save({ ...student, skills: next }); })}>Remove</button></div>)}</div></fieldset> : <p>Save this new profile to add its skills.</p>}</section></div>}
 {page === 'Careers' && <><div className="section-head"><input aria-label="Filter careers" placeholder="Filter by career title…" value={filter} onChange={e => setFilter(e.target.value)}/><span className="muted">Top five matches · select up to 3 to compare</span></div><div className="career-list">{!careers.filter(c => c.label.toLowerCase().includes(filter.toLowerCase())).length && <div className="card"><h2>No careers match “{filter}”</h2><p>Try a shorter title or clear the filter to see your recommendations.</p><button className="secondary" onClick={() => setFilter('')}>Clear filter</button></div>}{careers.filter(c => c.label.toLowerCase().includes(filter.toLowerCase())).slice(0, 5).map((c, i) => <article className="card career" key={c.id}><div className="career-top"><span className="rank">{String(i + 1).padStart(2, '0')}</span><div><h2>{c.label}</h2><small>{c.source}</small></div><strong className="score">{c.score.toFixed(1)}<small>/100</small></strong></div><p>{c.description}</p><div className="grid two"><div><h3>Supporting skills</h3>{tags(c.matching, 'match')}</div><div><h3>Essential gaps</h3>{tags(c.missing_essential, 'missing')}</div></div><div className="career-actions"><label className="checkbox"><input type="checkbox" checked={compare.includes(c.id)} onChange={e => setCompare(e.target.checked ? [...compare.slice(-2), c.id] : compare.filter(x => x !== c.id))}/>Compare</label><button className="secondary" onClick={() => { setTarget(c.id); go('Skill gaps'); }}>View details & skill gap <ArrowUpRight size={16}/></button></div></article>)}</div>{compare.length > 0 && <section className="card"><h2>Career comparison</h2>{chart(careers.filter(c => compare.includes(c.id)).map(c => ({ label: c.label, coverage: c.coverage, semantic: c.components.semantic * 100, ml: c.components.ml * 100 })), 300, ['coverage', 'semantic', 'ml'])}</section>}</>}
 {page === 'Skill gaps' && selected && <><div className="toolbar">{careerSelect}{addControl}</div><div className="grid dashboard-grid"><section className="card"><div className="section-head"><h2>{selected.label}</h2><div className="match-summary"><strong className="score" data-testid="matching-score">{selected.score.toFixed(2)}<small>/100 match</small></strong><span>{selected.coverage.toFixed(1)}% weighted skill coverage</span></div></div>{chart([{ label: 'Weighted coverage', score: selected.coverage }, { label: 'Semantic match', score: selected.components.semantic * 100 }, { label: 'ML similarity', score: selected.components.ml * 100 }], 210)}<p>{selected.explanation}</p><div className="contributions">{Object.entries(selected.contributions).map(([k, v]) => <span key={k}>{k}<strong>{v.toFixed(2)} points</strong></span>)}</div><h3>Semantic evidence</h3>{selected.semantic_evidence.length ? selected.semantic_evidence.map(e => <p key={e.required}>{e.related_known.map(label).join(', ')} → {label(e.required)}: {e.credit} partial credit, {e.source}. Requirement remains missing.</p>) : <p className="muted">No partial related-skill matches for this profile.</p>}</section><section className="card"><h3>Matching skills</h3>{tags(selected.matching, 'match')}<h3 className="spaced">Missing essential skills</h3>{tags(selected.missing_essential, 'missing')}<h3 className="spaced">Additional useful skills</h3>{tags(selected.optional, 'optional')}<p className="caption">Presence-based coverage; no official proficiency targets are assumed.</p><button onClick={() => go('Learning roadmap')}>Build your roadmap <ArrowRight size={16}/></button></section></div></>}
 {page === 'Knowledge graph' && graph && <><div className="toolbar">{careerSelect}<a className="button secondary" href="/api/graph/triples" download="skillgraph.ttl"><Download size={16}/>Download RDF</a></div><div className="grid graph-grid"><section className="card graph-card"><div className="section-head"><h2>Connections behind the recommendation</h2><span className="muted">{graph.triple_count} RDF triples</span></div><Suspense fallback={<div className="graph chart-loading">Loading knowledge graph…</div>}><GraphView elements={graph.elements} onInspect={setInspect}/></Suspense><div className="tags"><span className="tag match">Matching skill</span><span className="tag missing">Missing skill</span><span className="tag optional">Related skill</span><span className="muted">Pan · Scroll to zoom · Click nodes or edges</span></div></section><section className="card"><h2>Inspect the evidence</h2>{inspect ? <dl>{Object.entries(inspect).map(([k, v]) => <React.Fragment key={k}><dt>{k}</dt><dd>{String(v)}</dd></React.Fragment>)}</dl> : <p>Select a node or edge to inspect its label, relationship, and source.</p>}</section></div><details className="card advanced-tools"><summary>Query the semantic graph</summary><div className="section-head"><h2>SPARQL examples</h2><select aria-label="Example SPARQL" onChange={e => setQuery(graph.queries[e.target.value])}><option value="shared">Shared skill paths</option><option value="requirements">Essential requirements</option><option value="prerequisites">Curated prerequisites</option></select></div><label>SPARQL SELECT<textarea className="code" rows={5} value={query} onChange={e => setQuery(e.target.value)}/></label><button onClick={() => run(async () => setQueryResult(await api('/graph/query', { method: 'POST', ...json({ query }) })))}>Run query <ArrowRight size={15}/></button>{queryResult && <div className="table-scroll"><table><thead><tr>{queryResult.columns.map((c: string) => <th key={c}>{c}</th>)}</tr></thead><tbody>{queryResult.rows.map((r: string[], i: number) => <tr key={i}>{r.map((v, j) => <td key={j}>{v}</td>)}</tr>)}</tbody></table><p>{queryResult.rows.length} rows · response capped at 500</p></div>}</details></>}
 {page === 'Learning roadmap' && student && <><div className="toolbar">{careerSelect}<label className="checkbox"><input type="checkbox" checked={acquired} onChange={e => setAcquired(e.target.checked)}/>Also record completed skills as acquired at {level}/5</label><select aria-label="Acquired proficiency" value={level} onChange={e => setLevel(+e.target.value)}>{[1, 2, 3, 4, 5].map(n => <option key={n} value={n}>{n}/5</option>)}</select></div><div className="notice"><Route size={20}/><p>Prerequisites come first; then essential skills; ties sort alphabetically. Effort is a project estimate. Marking acquired updates recommendations and removes the skill from the gap.</p></div>{steps.length === 0 ? <section className="card">No missing requirements. Build a portfolio project to test and demonstrate your skills.</section> : steps.map(s => <article className={'card roadmap-step ' + (s.completed ? 'completed' : '')} key={s.skill}><div className="stage">{s.completed ? <Check /> : String(s.stage).padStart(2, '0')}</div><div><div className="section-head"><h2>{s.label}</h2><span className="tag optional">{s.importance}</span></div><p>{s.objective}</p><p><strong>Practice:</strong> {s.practice}</p><p className="muted">Prerequisites: {s.prerequisites.map(label).join(', ') || 'None known'} · Estimated effort: {s.estimated_hours} hours</p><label className="checkbox"><input aria-label={'Complete ' + s.label} type="checkbox" checked={s.completed} disabled={busy} onChange={e => { const checked = e.target.checked; setSteps(old => old.map(x => x.skill === s.skill ? { ...x, completed: checked } : x)); run(async () => { await api(`/students/${student.id}/progress?occupation=${encodeURIComponent(target)}&skill=${encodeURIComponent(s.skill)}`, { method: 'PUT', ...json({ completed: checked, acquired, proficiency: level }) }); await refresh(student); }); }}/>Mark complete</label></div></article>)}</>}
 {page === 'Knowledge graph' && insights && <details className="technical-details"><summary>Technical details & data</summary><div className="technical-content"><div className="grid three"><section className="card"><FlaskConical className="accent"/><h3>Active representation</h3><p>{insights.model.model}</p><p>{insights.model.occupation_count} occupations · {insights.model.feature_count} features · {insights.model.components} dimensions</p><small>Random state {insights.model.random_state}</small></section><section className="card"><Network className="accent"/><h3>Semantic graph</h3><p>{insights.triple_count} RDF triples</p><p>RDFLib · OWL classes · SKOS vocabulary · reified relationship provenance</p></section><section className="card"><ChartNoAxesCombined className="accent"/><h3>Scoring weights</h3><p>Coverage {insights.weights.coverage * 100}% · Graph {insights.weights.semantic * 100}% · ML {insights.weights.ml * 100}%</p><p>Essential {insights.weights.essential_weight} : optional {insights.weights.optional_weight}<br />Related-concept credit {insights.weights.related_credit}</p></section></div><section className="card"><h2>Evaluation evidence</h2><p>{insights.evaluation?.description || 'No evaluation has run yet. Run scripts/evaluate.py to produce evidence.'}</p>{insights.evaluation && <><div className="table-scroll"><table><thead><tr><th>Method</th><th>Mean held-out skill recall@3</th><th>Median latency (ms)</th></tr></thead><tbody>{insights.evaluation.summary.map((r: any) => <tr key={r.method}><td>{r.method}</td><td>{r.recall_at_3.toFixed(3)}</td><td>{r.median_latency_ms.toFixed(3)}</td></tr>)}</tbody></table></div><p className="caption">Proxy experiment on curated catalog, not independent career relevance or accuracy. No student outcome labels used. The hidden skill is excluded from each query.</p></>}<details><summary>Model provenance</summary><pre>{JSON.stringify(insights.model, null, 2)}</pre></details></section><section className="card"><h2>Dataset provenance</h2><p>{insights.warning}</p><p>Active occupation sources: {insights.model.sources.join('; ')}</p><div className="table-scroll"><table><thead><tr><th>Source</th><th>Import evidence</th></tr></thead><tbody>{insights.imports.length ? insights.imports.map((i: any, n: number) => <tr key={n}><td>{i.source}</td><td><pre>{JSON.stringify(i, null, 2)}</pre></td></tr>) : <tr><td>Official datasets</td><td>Not yet imported. Bundled DEMO DATA only.</td></tr>}</tbody></table></div><p><a href="https://data.mendeley.com/datasets/rv6scbpd7v/1">Student Skill Gap Analysis</a> · <a href="https://esco.ec.europa.eu/en/use-esco/download">Official ESCO</a> · <a href="https://data.mendeley.com/datasets/4spj4mbpjr/2">Student Career Dataset</a></p></section><section className="card"><h2>Inspect & import a student CSV</h2><p>Names and emails are omitted from exports. Unknown skills are reported, never silently treated as known. ESCO catalogs import through the local CLI.</p><input aria-label="Student CSV" type="file" accept=".csv" onChange={e => { setFile(e.target.files?.[0] || null); setSchema(null); setImportResult(null); }}/><button className="secondary" disabled={!file} onClick={() => run(async () => { const f = new FormData(); f.append('file', file!); setSchema(await api('/datasets/inspect', { method: 'POST', body: f })); })}>Inspect schema</button>{schema && <><p>{schema.rows} source rows</p><div className="grid three">{['skills', 'languages', 'soft_skills', 'rating', 'career', 'year', 'course'].map(k => <label key={k}>{k}<select value={mapping[k] || ''} onChange={e => setMapping({ ...mapping, [k]: e.target.value })}><option value="">Not mapped</option>{schema.columns.map((c: string) => <option key={c}>{c}</option>)}</select></label>)}</div><label>Source attribution<input value={source} onChange={e => setSource(e.target.value)}/></label><button onClick={() => run(async () => { const f = new FormData(); f.append('file', file!); f.append('mapping', JSON.stringify(mapping)); f.append('source', source); setImportResult(await api('/datasets/import', { method: 'POST', body: f })); setInsights(await api('/insights')); })}>Validate & import</button></>}{importResult && <pre>{JSON.stringify(importResult, null, 2)}</pre>}</section></div></details>}
 </>}
 <footer className="app-footer"><span>SkillGraph · Explainable career exploration</span><span>Skills are self-reported. Results are a matching index, not a prediction.</span></footer>
 </div></main></div>;
}
createRoot(document.getElementById('root')!).render(<App />);

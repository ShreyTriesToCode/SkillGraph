import { ArrowRight, ArrowUpRight, Check, Network, Route, FlaskConical, GitBranch } from 'lucide-react';
type Requirement = {
    skill: string;
    label: string;
};
type Props = {
    student: {
        name: string;
        skills: Record<string, number>;
    } | null;
    career: {
        label: string;
        score: number;
        coverage: number;
        matching: Requirement[];
        missing_essential: Requirement[];
    } | undefined;
    steps: {
        skill: string;
        label: string;
        estimated_hours: number;
        completed: boolean;
    }[];
    go: (p: string) => void;
};
export default function Overview({ student, career, steps, go }: Props) {
    const known = career?.matching.slice(0, 3) || [];
    const gap = career?.missing_essential[0];
    const next = steps.find(s => !s.completed);
    return <>
  <section className="overview-hero" aria-labelledby="overview-title">
   <div className="hero-copy" data-enter>
    <h1 id="overview-title">Career direction,<br />built from your skills.</h1>
    <p>See where your skills can take you, understand what’s missing, and decide what to learn next.</p>
    <div className="hero-actions"><button onClick={() => go('Profile')}>Start your analysis <ArrowUpRight size={18}/></button><button className="text-button" onClick={()=>go('Careers')}>See career matches <ArrowRight size={18}/></button></div>
    <div className="hero-assurance"><span className="tiny-dot"/>Local prototype<span>Self-reported skills</span></div>
   </div>
   <div className="connection-board" aria-label="Live preview of the selected student's skill connections">
    <div className="board-heading"><span><GitBranch size={17}/>Your career connections</span><span className="live-dot">Live data</span></div>
    <div className="connection-diagram">
     <svg viewBox="0 0 520 380" preserveAspectRatio="none" aria-hidden="true"><path d="M95 73 C180 73 175 190 270 190 M95 190 L270 190 M95 307 C180 307 175 190 270 190 M270 190 C360 190 350 110 440 110"/><path className="gap-path" d="M270 190 C360 190 350 284 440 284"/><circle cx="270" cy="190" r="5"/></svg>
     <div className="diagram-known">{known.length ? known.map(s => <button key={s.skill} className="connection-skill" onClick={() => go('Skill gaps')}><Check size={15}/>{s.label}</button>) : <span className="muted">Add skills to see connections</span>}</div>
     <div className="diagram-person"><div className="person-icon"><Network size={28}/></div><strong>{student?.name || 'Your profile'}</strong><span>{student ? Object.keys(student.skills).length : 0} skills connected</span></div>
     <button className="diagram-career" onClick={() => go('Skill gaps')}><BriefcaseMark /><strong>{career?.label || 'Career match'}</strong><span>{career ? career.score.toFixed(1) : '—'} <small>/ 100 match</small></span><ArrowUpRight size={16}/></button>
     <button className="diagram-gap" onClick={() => go('Learning roadmap')}><span className="gap-mark"/> <div><small>Essential gap</small><strong>{gap?.label || 'Build your portfolio'}</strong></div><ArrowUpRight size={16}/></button>
    </div>
    <div className="board-footer"><span><i className="legend-known"/>Matching skill</span><span><i className="legend-gap"/>Essential gap</span><button className="text-button" onClick={() => go('Knowledge graph')}>Open graph <ArrowUpRight size={15}/></button></div>
   </div>
  </section>
  <section className="next-move" aria-labelledby="next-move-heading">
   <div className="next-move-intro"><Route size={26}/><h2 id="next-move-heading">Your next learning step.</h2><p>Your roadmap puts prerequisites first, so each new skill has something to build on.</p><button className="text-button" onClick={() => go('Learning roadmap')}>See your roadmap <ArrowRight size={17}/></button></div>
   <div className="next-move-detail"><div className="next-move-meta"><span>{career?.label || 'Your target career'}</span><span>{next ? `${next.estimated_hours} hours estimated` : 'Profile-based roadmap'}</span></div><h3>{next?.label || 'Choose your first skill'}</h3><p>{next ? 'Practice this skill, record your progress, and see how your career matches change.' : 'Add your skills to build a learning plan around your target occupation.'}</p><button className="secondary" onClick={() => go(next ? 'Learning roadmap' : 'Profile')}>{next ? 'Start learning' : 'Add your skills'}<ArrowUpRight size={17}/></button></div>
  </section>
  <section className="method-strip"><div><FlaskConical size={22}/><h2>Understand the recommendation.</h2></div><p>Weighted skill coverage, graph relationships, and learned similarity contribute to each result. Inspect the evidence behind every score.</p><button className="text-button" onClick={() => go('Knowledge graph')}>See the evidence <ArrowRight size={17}/></button></section>
 </>;
}
function BriefcaseMark() { return <svg width="21" height="21" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" aria-hidden="true"><rect x="3" y="7" width="18" height="14" rx="2"/><path d="M8 7V4h8v3M3 12c5 4 13 4 18 0M12 12v5"/></svg>; }

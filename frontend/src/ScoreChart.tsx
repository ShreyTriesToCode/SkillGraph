import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Legend } from 'recharts';
export default function ScoreChart({ data, height, keys }: {
    data: any[];
    height: number;
    keys: string[];
}) {
    return <div className="score-chart" style={{ height }} role="img" aria-label={data.map(x => `${x.label}: ${keys.map(k => `${k} ${Number(x[k]).toFixed(1)}`).join(', ')}`).join('; ')}><ResponsiveContainer><BarChart data={data} layout="vertical" margin={{ left: 0, right: 25 }}><CartesianGrid stroke="#dce5eb" horizontal={false}/><XAxis type="number" domain={[0, 100]} tickLine={false} axisLine={false} tick={{ fill: '#52616e', fontSize: 12 }}/><YAxis type="category" dataKey="label" width={130} tickLine={false} axisLine={false} tick={{ fontSize: 12, fill: '#314954' }}/><Tooltip cursor={{ fill: '#edf3fa' }} contentStyle={{ borderRadius: 12, border: '1px solid #d7e1e8' }}/>{keys.map((k, i) => <Bar key={k} dataKey={k} name={k} fill={['#204cda', '#167765', '#a65b21'][i]} radius={[0, 3, 3, 0]} barSize={18} isAnimationActive={false}/>)}{keys.length > 1 && <Legend />}</BarChart></ResponsiveContainer></div>;
}

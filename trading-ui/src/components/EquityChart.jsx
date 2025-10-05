import { LineChart, Line, XAxis, YAxis, CartesianGrid, ResponsiveContainer } from "recharts";
export default function EquityChart({ data=[] }) {
  return (
    <div className="h-56">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data}>
          <CartesianGrid stroke="#262626" />
          <XAxis dataKey="x" tick={{ fill:"#9ca3af", fontSize:12 }} />
          <YAxis tick={{ fill:"#9ca3af", fontSize:12 }} />
          <Line type="monotone" dataKey="y" stroke="#10b981" dot={false} strokeWidth={2}/>
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

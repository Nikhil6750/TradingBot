export default function ModelSelector({ value, onChange }) {
  return (
    <div style={{display:"flex", alignItems:"center", gap:8}}>
      <span style={{fontSize:12, color:"#a3a3a3"}}>Model</span>
      <select
        value={value}
        onChange={e=>onChange(e.target.value)}
        style={{height:32, background:"#0f0f0f", color:"#e5e5e5", border:"1px solid #262626", borderRadius:10, padding:"0 10px"}}
      >
        <option value="gpt-4o">GPT-4o</option>
        <option value="gpt-4o-mini">GPT-4o mini</option>
        <option value="gpt-3.5-turbo">GPT-3.5</option>
      </select>
    </div>
  );
}

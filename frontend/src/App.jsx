export default function App() {
  return (
    <main className="container">
      <h1>🌏 全球市场全景数据库</h1>
      <p>W02 Global Market Database</p>

      <section className="card">
        <h2>当前状态</h2>
        <p>前端基础框架已建立。</p>
        <p>下一步将接入 data/current 中的真实市场数据。</p>
      </section>

      <section className="card">
        <h2>计划模块</h2>
        <ul>
          <li>全球指数概览</li>
          <li>沪深300成分股数据库</li>
          <li>估值与资金流分析</li>
          <li>历史行情查询</li>
        </ul>
      </section>
    </main>
  );
}

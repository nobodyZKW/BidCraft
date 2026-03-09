const cards = [
  { title: "项目列表", desc: "创建采购项目、查看状态、搜索。" },
  { title: "需求录入", desc: "表单 + 自然语言输入，运行抽取。" },
  { title: "条款装配", desc: "查看候选条款并人工切换。" },
  { title: "风险校验", desc: "展示 High/Medium/Low 风险与定位。" },
  { title: "预览导出", desc: "导出草稿/正式版（docx、pdf）。" },
];

export default function Home() {
  return (
    <main
      style={{
        minHeight: "100vh",
        margin: 0,
        padding: "40px 20px",
        background:
          "radial-gradient(circle at 20% 20%, #f8f4df 0%, #f5f5f5 45%, #ffffff 100%)",
        fontFamily: "'Segoe UI', 'PingFang SC', sans-serif",
      }}
    >
      <div style={{ maxWidth: 960, margin: "0 auto" }}>
        <h1 style={{ marginBottom: 8, fontSize: 42 }}>BidCraft AI</h1>
        <p style={{ marginBottom: 28, color: "#333" }}>
          采购文件智能生成系统 MVP 前端骨架（Next.js）。
        </p>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
            gap: 16,
          }}
        >
          {cards.map((item) => (
            <section
              key={item.title}
              style={{
                border: "1px solid #d8d5c2",
                borderRadius: 12,
                padding: 16,
                background: "#fffdfa",
              }}
            >
              <h3 style={{ marginTop: 0 }}>{item.title}</h3>
              <p style={{ marginBottom: 0, color: "#4a4a4a" }}>{item.desc}</p>
            </section>
          ))}
        </div>
      </div>
    </main>
  );
}

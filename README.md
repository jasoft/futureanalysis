# 期货账户盈亏分析报表

基于 `futures_account_status_2024-09_to_2026-02.csv` 生成一个 Streamlit 分析页面，重点展示：

- 月度净入金
- 月度交易盈亏
- 手续费影响
- 扣手续费后的净盈亏
- 账户权益曲线
- 最大回撤
- 风险度变化

## 运行

```bash
uv sync
uv run streamlit run app.py
```

默认会自动扫描当前目录下的 `futures_account_status_*.csv` 文件。

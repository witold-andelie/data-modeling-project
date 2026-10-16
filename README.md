# Customer 360 — Relational and Graph Database Coursework

这是数据库课程项目。目标是对同一份 Olist 真实数据完成 **MySQL + Neo4j** 实现，验证同一组查询和约束，并保留可供 SAP IT Data & Analytics 面试展示的工程证据。

真实 Olist 快照已准备并核对原始文件 SHA-256：99,441 个订单、96,096 个客户、九类实体。**MySQL 与 Neo4j 全量导入、Q1–Q5、各 22 项约束审计、各五组约束负例和真实样本断言均已通过，结果与独立 Python 计算三方一致**。数据库实现阶段已完成；教师咨询与报告交付另行完成。当前证据见 `docs/validation-status.md` 和 `artifacts/delivery-status.json`。

两个项目容器已在验证结束后正常停止，数据卷保留。Docker inspect 确认 MySQL 实际上限 512MiB、Neo4j 实际上限 1GiB；结束时均为退出码 0、未被 OOM 终止。后续演示仍按单库启动。

数据挖掘属于另一门课程：本项目提供版本化文件接口，不训练模型、不实施聚类、分类、推荐或关联规则算法。报告正文和封面继续按用户要求暂缓。

## 结构

| 路径 | 用途 |
|---|---|
| `docs/requirements.md` | 作业要求、验收证据与完成状态 |
| `docs/design.md` | 业务边界、实体、口径、模型取舍与规范化计划 |
| `docs/normalization.md` | 候选键、函数依赖、BCNF 论证及高阶范式边界 |
| `docs/queries-and-constraints.md` | Q1–Q5 / C1–C5 的英文描述与形式化定义 |
| `models/*.puml` | 概念、关系实现、图实现三张 UML 源码 |
| `sql/`, `cypher/` | DDL、五组业务查询、约束审计 |
| `src/c360/` | 数据准备、加载、结果比较、外部分析接口 |
| `contracts/` | 数据挖掘接口说明与 JSON Schema |
| `data/raw/`, `data/processed/` | 原始 CSV、带校验值的规范化数据快照 |
| `artifacts/` | 本地检查、数据库查询、比较和接口输出证据 |
| `tests/` | 明确标注为合成数据的自动化测试 |
| `paper/` | 七节报告目录与证据映射；暂不写正文和封面 |

## 先运行不需要数据库的检查

在项目根目录使用 PowerShell：

```powershell
py -3 scripts/check_framework.py
py -3 -m unittest discover -s tests -v
py -3 scripts/c360.py --help
py -3 scripts/verify_local.py
```

核心数据准备与接口只使用 Python 标准库。数据库加载另需驱动：

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[databases]"
Copy-Item .env.example .env
docker compose config --quiet
powershell -File scripts/start-database.ps1 -Service mysql
```

启动前打开 Docker Desktop（Linux containers）。MySQL 使用本机端口 `3307`；Neo4j Browser 为 `http://localhost:7475`，Bolt 为 `7688`。默认仅绑定本机。密码通过 `.env` 配置，不提交该文件。镜像版本采用 MySQL 8.4 与 Neo4j 5.26 Community；首次成功运行后记录实际镜像摘要与驱动版本。

当前按低内存方式运行：**MySQL 硬上限 512MiB，Neo4j 硬上限 1GiB，默认轮流启动**。切换到图数据库使用 `powershell -File scripts/start-database.ps1 -Service neo4j`；如果另一个数据库仍在运行，脚本会退出，让现有任务继续。已运行的目标容器只检查限额，不自动停止或重建。容器禁用额外 swap；超出限额的操作可能失败，应缩小批次处理。Docker Desktop 与 WSL 的额外开销不包含在这两个容器的限额内。配置修改需要在当前任务结束后创建或重建容器才能生效；必须用 `docker inspect` / `docker stats` 核实。

`verify_databases.py` 现在要求明确选择一个库，或仅比较已保存文件，不再同时连接两库。全量 Python 离线计算、数据库加载/查询和 UML 渲染分别运行。启动脚本会保存实际内存限额及镜像摘要到 `artifacts/runtime/`；这些是检查时的证据，不能替代以后运行时的重新检查。

## 真实数据准备

从 [Olist 原始发布页](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce) 获取数据，保留其许可与版本信息，将以下原始 CSV 放到 `data/raw/`：

```text
olist_customers_dataset.csv
olist_orders_dataset.csv
olist_order_items_dataset.csv
olist_products_dataset.csv
olist_sellers_dataset.csv
olist_order_payments_dataset.csv
olist_order_reviews_dataset.csv
```

本阶段不使用地理坐标文件或品类翻译文件；品类保留原始名称。数据来源核验记录在 `docs/sources.md`，最终数据版本和许可文本还需随下载归档。

```powershell
py -3 scripts/c360.py prepare
```

输出 `data/processed/quality.json` 和通过校验的 `dataset.json`。每类至少 5 条；原始字段解析失败、重复键、断开的引用或业务约束异常会阻止数据集发布，不会自动删除问题记录。先检查质量报告，再制定有记录的清洗政策。不要用测试夹具代替真实实例。

## 双数据库运行

```powershell
.\.venv\Scripts\python.exe scripts/c360.py load mysql
.\.venv\Scripts\python.exe scripts/c360.py load neo4j
```

每个数据库承载一个不可变快照。同一快照完成后重复加载为无操作；不同快照拒绝覆盖。MySQL 使用带超时的纯 Python 连接器；Neo4j 中断后可恢复同一快照的 MERGE 加载。节点和关系均按默认 500 行分批，可用 `load ... --batch-size 100` 缩小批次。只运行一个加载进程。不要手工修改已完成的快照；没有自动删除数据库或卷的命令。

将 `config/query-parameters.json` 中 `customer_id` 替换为真实的统一客户 ID。时间窗口是左闭右开，时间使用原始数据的本地、无时区语义。

```powershell
.\.venv\Scripts\python.exe scripts/c360.py query mysql Q1 --out artifacts/mysql-Q1.json
.\.venv\Scripts\python.exe scripts/c360.py query neo4j Q1 --out artifacts/neo4j-Q1.json
py -3 scripts/c360.py compare artifacts/mysql-Q1.json artifacts/neo4j-Q1.json --out artifacts/compare-Q1.json
.\.venv\Scripts\python.exe scripts/c360.py query mysql constraints --out artifacts/mysql-constraints.json
.\.venv\Scripts\python.exe scripts/c360.py query neo4j constraints --out artifacts/neo4j-constraints.json
```

对 Q2–Q5 同样执行，并确认约束审计各行 `violations = 0`。比较器检查数据快照、查询编号和参数一致，忽略行顺序但保留重复行。**两边相等并不能单独证明结果正确**，还须使用手工可核对的真实小样本进行业务断言；Q5 无结果也不自动证明数据错误。

离线准备独立 Python 期望结果和带完整父引用的真实展示样本（九类各至少五条），随后仅验证当前运行的数据库：

```powershell
py -3 scripts/build_reference.py
py -3 scripts/profile_source.py
.\.venv\Scripts\python.exe scripts/verify_databases.py --engine mysql
.\.venv\Scripts\python.exe scripts/probe_constraints.py --engine mysql
.\.venv\Scripts\python.exe scripts/verify_real_cases.py --engine mysql
```

查询结果、计划、版本、一次执行的耗时和负例证据归档到 `artifacts/database-verification/`。主验证器只读；负例脚本在事务中尝试无效写入并始终回滚，随后重新审计。真实样本的固定金额断言保存在 `config/real-sample-assertions.json`，可核对 1792+5263=7055 分、零付款订单及同一客户的两笔订单合计 56588 分。

本任务启动的项目库在验证结束、确认没有其他任务使用后，可以按用户已授权的流程正常停止，再切换另一库；不需要重复确认。不能停止其他终端使用的容器，也不删除数据卷。切换后用相同参数运行 Neo4j 三个验证命令，最后离线比较文件：

```powershell
.\.venv\Scripts\python.exe scripts/verify_databases.py --engine neo4j
.\.venv\Scripts\python.exe scripts/probe_constraints.py --engine neo4j
.\.venv\Scripts\python.exe scripts/verify_real_cases.py --engine neo4j
py -3 scripts/verify_databases.py --compare-only
py -3 scripts/check_delivery.py
```

Neo4j Community 的 C1 唯一性由原生约束拒绝；C2–C5 由审计检测。不要把审计检测描述成阻止任意写入。记录的一次耗时不构成受控性能排名。

## 留给另一门课的接口

```powershell
py -3 scripts/c360.py export-features --start 2017-01-01T00:00:00 --end 2018-01-01T00:00:00 --out artifacts/customer-features.json
py -3 scripts/c360.py validate-results external-results.json --features artifacts/customer-features.json
```

输出客户级订单数、付款总额与最近购买时间等基础聚合，不做数据挖掘。Olist 是历史快照，付款没有完整的历史可见时间，因此接口明确声明 `point_in_time_safe=false`。不能把观察窗口当作已实现防泄漏的时间点特征系统。

外部结果校验要求客户属于对应快照、模型版本明确、客户不重复。当前接入边界是文件校验，不包含数据库结果持久化、模型服务或 UI；后续需求明确后再增加独立扩展表/节点。

## UML 导出

```powershell
powershell -File scripts/render-models.ps1 -PlantUmlJar .tools/plantuml.jar
```

脚本使用本地 Java 和 PlantUML JAR，输出到 `artifacts/models/`。图源使用 Smetana 布局，不额外要求 Graphviz。最终交付 PNG 与 `.puml` 源码。先检查可读性，再放入 PDF。

## 当前验收与后续

`py -3 scripts/check_delivery.py` 核对数据覆盖、两库验证、负例、样本、三方比较、实际内存限额、UML 和特征接口。`artifacts/database-verification/summary.json` 保存六组最终比较，`artifacts/runtime/final-containers.json` 保存结束时的实际状态。

仓库保留三张 UML PNG、验证汇总、约束审计、查询计划和比较证据。原始 CSV、完整规范化快照、逐行查询结果、真实样本导出、客户特征文件、凭据和第三方工具不提交；这些文件需要按前面的步骤在本地生成。因此，全新克隆先查看已归档的验收结论；重新执行完整交付检查前，先准备数据并生成全部结果。

代码许可见 [LICENSE](LICENSE)。Olist 数据的独立来源、版本和许可记录见 [docs/sources.md](docs/sources.md)。

1. 演示时用启动脚本运行一个库；同一快照重复加载返回 `already_loaded`。
2. 进行三次真实教师咨询；不得编造日期或批准。
3. 待用户请求后撰写英文报告、封面及同一 PDF 末尾的源码附录。

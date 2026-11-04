# Abaqus Mesh Audit / 二维网格检查

读取 Abaqus `.inp`，输出可定位到节点和单元的 JSON 检查报告。Python 3.10+，纯标准库，无需安装 Abaqus，不修改输入，不运行求解器。

```sh
python mesh_audit.py examples/two-triangles.inp
python mesh_audit.py examples/square-q4.inp --output audit.json
python mesh_audit.py examples/inverted-triangle.inp
python -m unittest discover -s tests -v
```

Windows 可用 `py -3` 代替 `python`。反向三角形示例应返回退出码 1；其余两例返回 0。已有输出文件不会覆盖。

## 检查内容

- 非正/退化有向面积、重复连接节点。
- 三角形/Q4 最小内角，最长边/最短边比值。
- Q4 四个 Gauss 点、四角点和中心的 Jacobian。
- 完全重合的节点、相同节点集合的重复单元、超过两个单元共用的非流形边。
- 外露边数量及显式 ELSET 单元数量。

可用 `--min-angle 20 --max-edge-ratio 10` 修改筛查阈值。这些值是示例默认值，不是通用精度保证；边长比也不等于所有软件的 aspect ratio 定义。退化判据按单元最长边平方缩放。

## 支持范围

仅支持单一编号空间的显式 XY 网格：z=0；CPE3、CPS3、CPE4、CPE4R、CPS4、CPS4R。节点/单元记录须在单行内。支持显式数字 ELSET 和 GENERATE。

不支持 INCLUDE、PART/ASSEMBLY/INSTANCE、坐标变换/生成、高阶或三维单元、用户单元和命名 ELSET 引用。遇到不支持输入会报错，不能通过这个工具直接验证任意完整 Abaqus 模型。请先另行导出扁平网格。

## 如何理解结果

退出码 0：已声明的几何检查通过；1：发现网格问题；2：输入不支持/无效或输出失败。报告逐项列出问题和单元指标，并保留输入 SHA-256。

外露边可能是外边界、孔洞或裂缝，不能仅据此判定界面不相容。工具不做完整的单元相交/重叠搜索，也不证明多相界面归属、有限元解精度或物理模型正确。

## Agent Skill

让助手读取 [SKILL.md](skills/abaqus-mesh-audit/SKILL.md)，并保留整个仓库。所有示例均为合成网格，不含研究模型。MIT License；见 [PROVENANCE.md](PROVENANCE.md)。

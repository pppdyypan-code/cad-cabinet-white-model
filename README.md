# CAD柜体白模与机位

### 从CAD尺寸到Blender白模，先选对角度，再出高清。

面向衣帽间、定制柜体和室内效果图前期的 **Codex skill**。它让Codex复用参数化建模和批量机位脚本，把尺寸、设计决定与相机设置留在项目配置里，方便持续修改。

**读CAD → 参数化白模 → 多机位小样 → 选定高清。**

[安装与开始](#安装与开始) · [使用示例](#直接这样告诉codex) · [能力与边界](#能力与边界) · [English](#english)

![四个编号机位的Blender白模小样，包含柜体、门口与梳妆台视角](docs/example-proofs.png)

*仓库内的合成示例。小样用于选角度和检查几何，不代表最终材质效果。*

## 它能帮你解决什么

如果你经常对着效果图说“再退后一点”“梳妆台正一点”“柜子又被拉宽了”，这套流程就是为这类反复调整准备的。

| 常见问题 | 这套skill怎么处理 |
| --- | --- |
| 图纸有平面、立面和局部尺寸，每次续改又要解释一遍 | 将尺寸来源、冲突处理和估算记入项目配置，后续修改先读已有记录 |
| 每次做柜体都重新写门板、抽屉和拉手代码 | 复用常规柜体组件，用参数控制尺寸、分格与摆放 |
| 为了露全柜子越调越广，边缘比例难看 | 批量给出不同位置、焦距和视高的小样，对比完整入镜与自然比例的取舍 |
| 只想换角度，却重新生成整个房间 | 复用已有模型调整相机，比较修改前后的基础几何指纹 |
| 角度还没定，就反复等待高清渲染 | 先看编号小样，只渲染选定机位的高清图 |
| 换一次参数又把同样的工作跑一遍 | 验证源文件、配置和输出；符合条件时复用缓存，参数变化时拒绝误用过期模型 |

适合使用 **Codex + Blender** 的室内设计师、定制柜体设计师和效果图制作者，尤其是需要核对比例、门板分格、拉手位置和室内机位的项目。

## 一次项目会得到什么

1. **尺寸与设计记录**：项目JSON保存模型参数、尺寸依据、估算和相机设置。
2. **可编辑白模**：Blender场景，便于继续改尺寸或进入材质、灯光阶段。
3. **编号机位小样**：多视角PNG、离线HTML联系表；安装Pillow后还可生成一张并排对比图。
4. **选定机位的高清图**：默认长边2400px，可按项目调整；附对应场景和简短检查说明。

已有 `.blend` 也可以从调机位开始，不必重新建模。脚本在独立输出路径保存调整后的场景，保留输入文件。

## 安装与开始

需要本地可用的 **Codex、Blender和Python 3**。脚本使用Python标准库；Pillow可选，用于合成PNG联系表。已验证环境见 [验证记录](VALIDATION.md)。

### 方式一：让Codex安装

把下面这句话发给Codex：

> 请用skill-installer从 https://github.com/pppdyypan-code/cad-cabinet-white-model 安装 skills/cad-cabinet-white-model。

### 方式二：本地安装

下载仓库并在仓库目录运行 `python3 install.py`，或使用Git：

```bash
git clone https://github.com/pppdyypan-code/cad-cabinet-white-model.git
cd cad-cabinet-white-model
python3 install.py
```

默认安装到 `$CODEX_HOME/skills`，未设置时使用 `~/.codex/skills`。安装器不会覆盖已有同名skill。下一轮Codex即可使用；如果尚未识别，重新打开会话。

## 直接这样告诉Codex

**按CAD新建白模**——附上平面、立面和必要的局部尺寸图：

> 用 $cad-cabinet-white-model 按这组CAD做衣帽间白模。尺寸冲突以立面标注为准；保留门板分格、拉手和吊顶关系。先给衣柜完整视角、自然比例视角、梳妆台正面和门口全景的编号小样，选定后再出高清。

**调整已有场景的角度**——提供 `.blend` 文件：

> 用 $cad-cabinet-white-model 调整这个白模。梳妆台视高改成1.2m，画面更正一点，不改变柜体尺寸。先给我几个有差别的小样，并说明推荐哪个。

**选定后输出**：

> 选B机位，按这个构图输出长边2400px的高清白模，同时给我对应的Blender场景。

写出 `$cad-cabinet-white-model` 可以明确指定这套流程；后面的尺寸、视高、角度和输出要求照常用自然语言描述即可。

## 为什么有机会更省时间和token

省的是重复工作：复用现成脚本、读取已保存的项目参数、同一进程批量生成小样，以及只给选定角度渲染高清。必要的读图、尺寸判断和视觉检查仍然要做。

**目前没有同项目的端到端对照测试，因此不承诺具体提速或token节省比例。** 本地脚本执行时间、实际测试版本和检查范围见 [验证记录](VALIDATION.md)。

## 能力与边界

支持常规柜体、门板分格、抽屉前面板、格栅、bar/F/knob拉手、多边形挤出及45°门板边截面。内置尺寸与基础拓扑检查、机位包围盒入镜检查、批量预览和选定机位渲染。

- **需要读图判断**：这是Codex工作流和本地脚本，不是自动识别所有DWG的工具。CAD读取与取舍由Codex结合提供的资料完成，缺失尺寸和估算要记录。
- **重点是白模与机位**：真实板材、灯光和最终写实效果需要后续材质与渲染工作；本skill不保证消除AI图像生成的失真。
- **按项目补充造型**：内部滑轨、布帘、复杂曲面和特殊家具需要另外建模。
- **检查有范围**：包围盒在画内不代表没有遮挡；长焦也不自动保证自然透视。仍需对照图纸查看小样，基础拓扑检查不等于完整资产QA或制造精度认证。

运行脚本不需要云渲染服务、额外API密钥或生命周期hooks。Codex本身的模型用量及费用取决于你的使用方式。

本仓库只发布通用代码、文档和合成示例，不包含私人CAD、现场照片、客户尺寸表或个人本机路径。

## 命令行示例

在仓库根目录复制合成配置，再按自己的图纸修改尺寸、组件与相机：

```bash
cp skills/cad-cabinet-white-model/assets/example-project.json project.json
python3 skills/cad-cabinet-white-model/scripts/workflow.py validate --project project.json
python3 skills/cad-cabinet-white-model/scripts/workflow.py build --project project.json --out work/model
python3 skills/cad-cabinet-white-model/scripts/workflow.py preview --project project.json --blend work/model/model.blend --out work/proofs
python3 skills/cad-cabinet-white-model/scripts/workflow.py final --project project.json --blend work/model/model.blend --out work/final --cameras A C
```

完整配置见 [项目格式](skills/cad-cabinet-white-model/references/project-format.md)。默认小样长边640px，高清长边2400px；可用 `--size` 和 `--samples` 调整，`--blender` 指定Blender可执行文件，`--device CPU` 用于无GPU环境。

各视图可能有不同画幅或隐藏对象，请继续通过项目JSON与脚本渲染；单独在Blender里切换活动相机不会同步全部设置。

## 验证与反馈

```bash
python3 -m unittest discover -s tests -v
python3 tests/integration.py --blender /path/to/blender
```

已有检查覆盖尺寸、门板/抽屉数量、网格复用、45°截面、相机调整时的基础几何保持，以及缓存失效处理。仅宣称实际测试过的环境，详见 [验证记录](VALIDATION.md)。

遇到问题或希望增加组件，可以 [提交Issue](https://github.com/pppdyypan-code/cad-cabinet-white-model/issues)。请提供Blender版本、复现步骤和脱敏后的最小配置；分享图纸或截图前移除客户信息。

## English

**CAD Cabinet White Model** is a Codex skill for dimension-led cabinet modeling and camera planning in Blender. It is designed for walk-in closets, fitted cabinetry and interior visualization preparation.

It helps Codex record drawing dimensions, reuse parametric cabinet components, compare numbered camera previews and render only the selected views at full resolution. Existing Blender scenes can also be used for camera adjustments without rebuilding the room.

- **Input:** plans, elevations, dimensioned references, or an existing `.blend` scene.
- **Output:** a project configuration, editable Blender scene, camera proof sheets and selected full-resolution white-model images.
- **Install:** clone this repository and run `python3 install.py`, or ask Codex's skill-installer to install `skills/cad-cabinet-white-model` from this repository.
- **Use:** “Use $cad-cabinet-white-model to build a closet white model from these drawings. Record dimension assumptions, show distinct numbered camera previews, then render the views I select.”

Drawing interpretation and visual review remain necessary. This is not a universal DWG parser or a manufacturing certification tool. Photorealistic materials and lighting are a separate stage. No measured end-to-end speedup or token reduction is claimed. See [validation](VALIDATION.md) for tested behavior and limitations.

## License

[MIT](LICENSE). 可以使用、修改和分发，遵守许可证中的版权及许可声明要求。

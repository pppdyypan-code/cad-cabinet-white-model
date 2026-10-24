# 项目配置 v1

复制assets/example-project.json到任务工作目录。示例是合成房间，不是用户原项目。所有长度为mm；Blender内部一单位一米。

## 坐标和组件

房间原点为入口侧左下角，X向右、Y向深处、Z向上。room包含width_mm/depth_mm/height_mm/wall_mm；open_sides是展示时不生成的整墙/顶：front/back/left/right/ceiling。有洞口的墙用局部box/prism组件构成，把对应整墙列入open_sides。

components每项有唯一ASCII id、kind、position_mm:[x,y,z]、可选rotation_deg。位置是局部原点；局部X宽、Y深、Z高，柜前面在Y最大值。绕Z转动后定位，不用缩放修改尺寸。中文名称可放label。

- box：width_mm/depth_mm/height_mm，用于台面、吊顶、收口与分段墙。
- cabinet：同上；board_mm/door_mm/gap_mm默认18/18/3。columns各有width_mm，合计须等于总柜宽（0.1mm数值容差）；rows_mm从下到上定义该列前面板高度，合计等于柜高，默认整扇门。脚本生成前面板与柜体，内部抽屉盒/滑轨需另建。
- 列的handle：style:none/bar/f/knob，side:left/right/center，length_mm，orientation:vertical/horizontal。F型只支持竖向；横向用bar。具体截面按参考局部扩展。
- 列的miter_left/miter_right:true将面板对应边背面缩进一个门板厚度，形成45°截面。它不推导L形摆放；两侧位置、外露段和重叠须按图配置，用顶视检查拼接。
- slats：宽深高、count、bar_mm。按数量在总宽内均匀分布并复用网格。数量须来自图纸。
- prism：polygon_mm:[[x,y],...]及height_mm，沿Z挤出。输入必须是简单不自交轮廓，复杂轮廓另做几何处理。

## 机位与已有文件

cameras各有id、position_mm、target_mm、lens_mm、可选shift_x/shift_y、aspect:[宽,高]默认4:3。保持垂直线可令target的Z与position一致，再用shift_y取景。关闭景深以读清白模。

targets为需要检查入镜的组件ID或已有对象名/前缀。结果只判断包围盒，不知道是否被墙遮挡，必须看图。hide_objects为该视图明确允许隐藏的对象完整名称，记录在结果里；默认不隐藏。

mode:existing用于既有模型，可省略components，给机位及已有对象名即可。它不验证CAD一致性，但比较相机操作前后的几何指纹。默认mode:build会检查建模参数与源文件是否匹配。

## 依据与记录

decisions使用field/value/basis/source/note，basis可为dimensioned/user/estimated，保留尺寸优先级与用户授权。路径和CAD可以放私人项目配置里，发布通用技能时移除。

每次stage-result.json记录源文件指纹、Blender版本、几何指纹、机位、检查范围和渲染图。缓存匹配配置、源文件内容及脚本版本，--force强制重做。Pillow仅用于拼PNG联系表；缺少时仍输出各张PNG和可离线打开的HTML。

建模覆盖常规矩形柜体和指定多边形。布帘、特殊曲面、特定凳子、门窗五金按任务补建，不用默认积木代替指定造型。

import bpy
from . import utils


def _count_generated(guide_type=None):
    return len(utils.generated_objects(guide_type))


def _draw_status(layout, scene):
    box = layout.box()
    box.label(text="現在の状態:", icon='INFO')
    head = scene.hair_target_head_object
    if head and head.type == 'MESH':
        box.label(text=f"頭部: {head.name}", icon='CHECKMARK')
    else:
        box.label(text="頭部: 未設定", icon='ERROR')
        box.label(text="先に頭部メッシュを選択してください。")
    guide_objects = [obj for obj in utils.generated_objects() if obj.get("hair_guide_type") in {"guide", "region"}]
    basic_count = len([obj for obj in guide_objects if obj.get("hair_guide_level") == "basic"])
    detailed_count = len([obj for obj in guide_objects if obj.get("hair_guide_level") == "detailed"])
    point_count = _count_generated("placement_point")
    curve_count = _count_generated("curve")
    warning_count = _count_generated("warning")
    box.label(text=f"基本ガイド: {basic_count}", icon='OUTLINER_OB_CURVE')
    box.label(text=f"詳細ガイド: {detailed_count}", icon='OUTLINER_OB_CURVE')
    box.label(text=f"配置点: {point_count}", icon='MESH_UVSPHERE')
    box.label(text=f"カーブ: {curve_count}", icon='OUTLINER_OB_CURVE')
    box.label(text=f"警告: {scene.hair_warning_count or warning_count}", icon='ERROR' if (scene.hair_warning_count or warning_count) else 'CHECKMARK')


def _region_buttons(layout, label, region, note):
    row = layout.row(align=True)
    op = row.operator('hgd.region_visibility', text=f"{label}を表示", icon='HIDE_OFF')
    op.region = region
    op.action = 'SHOW'
    op = row.operator('hgd.region_visibility', text=f"{label}を非表示", icon='HIDE_ON')
    op.region = region
    op.action = 'HIDE'
    layout.label(text=note, icon='INFO')


class HGD_PT_base(bpy.types.Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'ヘアガイド'


class HGD_PT_quick_start(HGD_PT_base):
    bl_label = 'クイックスタート'
    bl_order = 0

    def draw(self, context):
        layout = self.layout
        box = layout.box()
        box.label(text="作業手順", icon='INFO')
        box.label(text="1. 頭部メッシュを選択")
        box.label(text="2. 頭部として登録")
        box.label(text="3. 基本ガイドを生成")
        box.label(text="4. 必要なら基本ガイドを移動")
        box.label(text="5. 配置点を生成/更新")
        box.label(text="6. 配置点を選択")
        box.label(text="7. 生成タイプを選びカーブ毛束を生成")
        box.label(text="8. 根元集中を確認")
        box.label(text="9. 必要ならカーブ形状で先細りを適用")
        box.label(text="円柱状なら: カーブ形状 → 全カーブへ適用", icon='INFO')
        _draw_status(layout, context.scene)


class HGD_PT_setup(HGD_PT_base):
    bl_label = 'セットアップ'
    bl_order = 1

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        layout.label(text="選択中の頭部メッシュを登録します。", icon='INFO')
        layout.label(text="既存メッシュは変更されません。")
        if not scene.hair_target_head_object:
            layout.label(text="頭部が未設定です。", icon='ERROR')
            layout.label(text="先に頭部メッシュを選択してください。")
        col = layout.column(align=True)
        col.prop(scene, 'hair_target_head_object')
        col.operator('hgd.set_target_head', text='選択メッシュを頭部として登録', icon='CHECKMARK')
        layout.separator()
        layout.prop(scene, 'hair_guide_scale')
        layout.prop(scene, 'hair_guide_offset')


class HGD_PT_guide_lines(HGD_PT_base):
    bl_label = 'ガイドライン'
    bl_order = 2

    def draw(self, context):
        layout = self.layout
        layout.label(text="髪型設計の基準となるガイドラインです。", icon='INFO')
        layout.label(text="基本は生え際・側面境界・後頭部・襟足・正中線です。")
        row = layout.row(align=True)
        op = row.operator('hgd.show_hide_guides', text='ガイド表示', icon='HIDE_OFF')
        op.hide = False
        op = row.operator('hgd.show_hide_guides', text='ガイド非表示', icon='HIDE_ON')
        op.hide = True
        layout.operator('hgd.create_hair_guides', text='基本ガイドを生成', icon='OUTLINER_OB_CURVE')
        layout.operator('hgd.create_hair_guides', text='基本ガイドを再生成', icon='OUTLINER_OB_CURVE')
        layout.operator('hgd.create_detailed_guides', text='詳細ガイドを追加', icon='OUTLINER_OB_CURVE')
        layout.label(text="基本ガイドのみ生成します。再実行しても基本のみ更新します。")
        layout.operator('hgd.delete_hair_guides', text='ガイド削除', icon='TRASH')
        layout.label(text="生成されたガイドのみ削除します。")
        layout.label(text="頭部メッシュは削除されません。")


class HGD_PT_regions(HGD_PT_base):
    bl_label = '領域表示'
    bl_order = 3

    def draw(self, context):
        layout = self.layout
        layout.label(text="髪の領域を表示・非表示します。", icon='INFO')
        _region_buttons(layout, "頭頂部", "Top", "頭頂部：前髪・横髪・後ろ髪へ分かれる毛流れの起点です。")
        _region_buttons(layout, "前髪", "Front", "前髪：前髪の開始位置。")
        _region_buttons(layout, "側頭部", "Side", "側頭部：耳周辺から後頭部へ流れる領域。")
        _region_buttons(layout, "左側", "Side_L", "左側のみ表示・非表示します。")
        _region_buttons(layout, "右側", "Side_R", "右側のみ表示・非表示します。")
        _region_buttons(layout, "後頭部上層", "Back_Upper", "後頭部上層：髪全体のボリューム。")
        _region_buttons(layout, "後頭部中層", "Back_Middle", "後頭部中層：大きな毛束を配置する領域。")
        _region_buttons(layout, "襟足", "Nape", "襟足：首へ向かって落ちる短い毛束領域。")
        row = layout.row(align=True)
        op = row.operator('hgd.region_visibility', text='全領域表示', icon='HIDE_OFF')
        op.region = 'ALL'
        op.action = 'SHOW'
        op = row.operator('hgd.region_visibility', text='全領域非表示', icon='HIDE_ON')
        op.region = 'ALL'
        op.action = 'HIDE'


class HGD_PT_placement(HGD_PT_base):
    bl_label = '配置点'
    bl_order = 4

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        layout.label(text="基本ガイドの位置を参照して、", icon='MESH_UVSPHERE')
        layout.label(text="毛束の根元候補を生成します。")
        layout.label(text="ガイドを動かしてから再生成すると、配置点も更新されます。")
        if not scene.hair_target_head_object:
            layout.label(text="頭部が未設定です。先にセットアップしてください。", icon='ERROR')
        if _count_generated("placement_point") == 0:
            layout.label(text="配置点がありません。", icon='ERROR')
            layout.label(text="配置点を生成/更新してください。")
        layout.operator('hgd.generate_placement_points', text='配置点を生成/更新', icon='MESH_UVSPHERE')
        layout.label(text="既存の配置点と警告は上書きされます。")
        layout.label(text="既存のカーブ毛束は削除されません。")
        layout.operator('hgd.clear_placement_points', icon='TRASH')
        layout.separator()
        layout.label(text="乱数シード：同じ値なら同じ配置になります。", icon='INFO')
        layout.label(text="左右対称性：高いほど左右対称になります。")
        layout.prop(scene, 'hair_seed')
        layout.prop(scene, 'hair_density')
        layout.prop(scene, 'hair_symmetry_bias')
        layout.prop(scene, 'hair_height_variation')
        layout.prop(scene, 'hair_width_variation')
        layout.prop(scene, 'hair_depth_variation')
        layout.prop(scene, 'hair_size_variation')
        layout.prop(scene, 'hair_length_variation')


class HGD_PT_curve_strand(HGD_PT_base):
    bl_label = 'カーブ毛束'
    bl_order = 5

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        layout.label(text="配置点から編集可能なBezierカーブ毛束を生成します。", icon='OUTLINER_OB_CURVE')
        layout.label(text="選択した配置点を使います。")
        layout.label(text="自動でメッシュ化はされません。")
        if _count_generated("placement_point") == 0:
            layout.label(text="配置点がありません。", icon='ERROR')
        if _count_generated("curve") == 0:
            layout.label(text="カーブ毛束はまだありません。", icon='INFO')
        layout.operator('hgd.create_curve_from_points', text='カーブ毛束を生成', icon='OUTLINER_OB_CURVE')
        layout.prop(scene, 'hair_strand_generation_type')
        layout.label(text="通常カーブ：1本の髪束ガイドを生成します。", icon='INFO')
        layout.label(text="三つ編み：制御カーブと表示用形状を生成します。")
        layout.prop(scene, 'hair_strand_type')
        layout.prop(scene, 'hair_curve_length')
        layout.prop(scene, 'hair_curve_bevel_depth')
        layout.prop(scene, 'hair_curve_resolution')
        layout.prop(scene, 'hair_curve_segment_count')
        layout.label(text="根元半径・毛先半径・先細りは", icon='INFO')
        layout.label(text="将来用の保存値です。")
        layout.prop(scene, 'hair_curve_root_radius')
        layout.prop(scene, 'hair_curve_tip_radius')
        layout.prop(scene, 'hair_curve_taper_strength')


class HGD_PT_braid(HGD_PT_base):
    bl_label = '三つ編み'
    bl_order = 6

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        layout.label(text="1本の制御カーブから", icon='OUTLINER_OB_CURVE')
        layout.label(text="三つ編み形状を生成します。")
        layout.label(text="形を変えたい場合は制御カーブを編集し、")
        layout.label(text="更新ボタンを押してください。")
        layout.prop(scene, 'hair_braid_segments')
        layout.prop(scene, 'hair_braid_width')
        layout.prop(scene, 'hair_braid_radius')
        layout.prop(scene, 'hair_braid_taper')
        layout.prop(scene, 'hair_braid_twist')
        layout.prop(scene, 'hair_braid_resolution')
        layout.prop(scene, 'hair_braid_bevel_depth')
        layout.prop(scene, 'hair_braid_auto_update')
        layout.label(text="自動更新は将来拡張です。現在は更新ボタンを使用してください。", icon='INFO')
        row = layout.row(align=True)
        row.operator('hgd.update_selected_braids', text='選択三つ編みを更新')
        row.operator('hgd.update_all_braids', text='全三つ編みを更新')


class HGD_PT_curve_shape(HGD_PT_base):
    bl_label = 'カーブ形状'
    bl_order = 7

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        layout.label(text="円柱状のカーブを、", icon='OUTLINER_OB_CURVE')
        layout.label(text="髪束らしい先細り形状にします。")
        layout.prop(scene, 'hair_use_shared_taper')
        layout.prop(scene, 'hair_auto_apply_taper_to_new_curves')
        layout.separator()
        layout.prop(scene, 'hair_taper_preset')
        layout.operator('hgd.apply_taper_preset', icon='CHECKMARK')
        layout.separator()
        layout.prop(scene, 'hair_taper_root_radius')
        layout.prop(scene, 'hair_taper_mid_radius')
        layout.prop(scene, 'hair_taper_tip_radius')
        layout.prop(scene, 'hair_taper_bevel_depth')
        layout.prop(scene, 'hair_taper_resolution')
        layout.label(text="毛先の太さを0にすると、先端が尖ります。", icon='INFO')
        layout.label(text="全体の太さはCurveのBevel Depthです。")
        layout.operator('hgd.create_or_update_default_taper', icon='OUTLINER_OB_CURVE')
        layout.separator()
        layout.label(text="適用:", icon='CHECKMARK')
        row = layout.row(align=True)
        row.operator('hgd.apply_taper_to_selected_curves', text='選択カーブへ適用')
        row.operator('hgd.apply_taper_to_all_curves', text='全カーブへ適用')
        layout.label(text="解除:", icon='TRASH')
        row = layout.row(align=True)
        row.operator('hgd.clear_taper_from_selected_curves', text='選択カーブのテーパー解除')
        row.operator('hgd.clear_taper_from_all_curves', text='全カーブのテーパー解除')


class HGD_PT_curve_batch_adjust(HGD_PT_base):
    bl_label = 'カーブ一括調整'
    bl_order = 8

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        layout.label(text="生成済みカーブをまとめて調整します。", icon='OUTLINER_OB_CURVE')
        layout.label(text="カーブ毛束生成後に使用します。")
        layout.label(text="長さ倍率は根元基準で変更します。", icon='INFO')
        layout.prop(scene, 'hair_batch_curve_length', text='長さ倍率')
        layout.prop(scene, 'hair_batch_curve_bevel_depth')
        layout.prop(scene, 'hair_batch_curve_resolution')
        row = layout.row(align=True)
        op = row.operator('hgd.apply_curve_batch_settings', text='選択カーブへ適用')
        op.target = 'SELECTED'
        op = row.operator('hgd.apply_curve_batch_settings', text='全カーブへ適用')
        op.target = 'ALL'


class HGD_PT_curve_follow(HGD_PT_base):
    bl_label = 'カーブ追従'
    bl_order = 9

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        layout.label(text="配置点移動後にカーブ根元を追従させます。", icon='INFO')
        layout.label(text="通常カーブと三つ編み制御カーブが対象です。")
        layout.prop(scene, 'hair_follow_update_selected_only')
        layout.prop(scene, 'hair_follow_keep_tip_offset')
        if not scene.hair_follow_keep_tip_offset:
            layout.label(text="毛先位置を維持しない場合、形が崩れることがあります。", icon='ERROR')
        layout.operator('hgd.update_curve_roots_from_points', icon='OUTLINER_OB_CURVE')


class HGD_PT_side_mirror(HGD_PT_base):
    bl_label = '左右ミラー'
    bl_order = 10

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        layout.label(text="側頭部の配置点、カーブ、三つ編みを", icon='INFO')
        layout.label(text="反対側へ複製します。")
        layout.label(text="選択中の左右対象のみ処理します。", icon='ERROR')
        layout.prop(scene, 'hair_mirror_axis')
        layout.label(text="MVPではX軸のみ対応します。")
        layout.prop(scene, 'hair_mirror_overwrite_existing')
        layout.prop(scene, 'hair_mirror_copy_custom_properties')
        row = layout.row(align=True)
        row.operator('hgd.mirror_side_l_to_r', text='左側→右側へミラー')
        row.operator('hgd.mirror_side_r_to_l', text='右側→左側へミラー')


class HGD_PT_validation(HGD_PT_base):
    bl_label = '検証'
    bl_order = 11

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        layout.label(text="同じ場所から毛束が生えて見える問題を検出します。", icon='INFO')
        layout.label(text="根元が近すぎる箇所を確認します。")
        if _count_generated("placement_point") == 0:
            layout.label(text="配置点がありません。", icon='ERROR')
            layout.label(text="検証前に配置点を生成してください。")
        layout.operator('hgd.check_root_clustering', icon='ERROR')
        layout.operator('hgd.clear_warnings', icon='TRASH')
        layout.prop(scene, 'hair_root_cluster_threshold')
        layout.prop(scene, 'hair_warning_count')
        layout.label(text="警告数は近すぎる配置点ペア数です。", icon='INFO')
        layout.label(text="赤色は根元が近すぎる警告です。")
        layout.label(text="Viewport ShadingのColorをObjectにしてください。")


class HGD_PT_display_cleanup(HGD_PT_base):
    bl_label = '表示と削除'
    bl_order = 12

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        layout.label(text="表示切替と削除を行います。", icon='INFO')
        layout.label(text="頭部メッシュに隠れて見えにくい場合に使用します。")
        layout.prop(scene, 'hair_show_guides_in_front')
        layout.operator('hgd.toggle_in_front_generated_helpers', icon='HIDE_OFF')
        layout.separator()
        row = layout.row(align=True)
        op = row.operator('hgd.show_hide_guides', text='ガイド表示', icon='HIDE_OFF')
        op.hide = False
        op = row.operator('hgd.show_hide_guides', text='ガイド非表示', icon='HIDE_ON')
        op.hide = True
        row = layout.row(align=True)
        op = row.operator('hgd.region_visibility', text='全領域表示', icon='HIDE_OFF')
        op.region = 'ALL'
        op.action = 'SHOW'
        op = row.operator('hgd.region_visibility', text='全領域非表示', icon='HIDE_ON')
        op.region = 'ALL'
        op.action = 'HIDE'
        layout.separator()
        layout.label(text="HairGuideSystem内の生成物のみ削除します。", icon='INFO')
        layout.operator('hgd.clear_warnings', icon='TRASH')
        layout.operator('hgd.clear_placement_points', icon='TRASH')
        layout.operator('hgd.delete_hair_guides', text='ガイド削除', icon='TRASH')
        layout.label(text="すべて削除はガイド、配置点、")
        layout.label(text="カーブ、警告、テーパーを削除します。")
        layout.label(text="頭部メッシュは削除されません。")
        layout.operator('hgd.clear_all_generated', icon='TRASH')


class HGD_PT_help(HGD_PT_base):
    bl_label = 'ヘルプ'
    bl_order = 13
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        box = layout.box()
        box.label(text="このアドオンでできること", icon='INFO')
        box.label(text="・髪のガイド生成")
        box.label(text="・毛束配置点生成")
        box.label(text="・Bezierカーブ毛束生成")
        box.label(text="・制御カーブ式の三つ編み生成")
        box.label(text="・カーブ毛束の先細り形状設定")
        box.label(text="・根元集中チェック")
        box = layout.box()
        box.label(text="できないこと", icon='ERROR')
        box.label(text="・髪メッシュ自動生成")
        box.label(text="・頭部メッシュ編集")
        box.label(text="・カーブの自動メッシュ化")
        box.label(text="・3本カーブの個別三つ編み編集")
        box.label(text="・Unity設定 / PhysBone設定")
        box = layout.box()
        box.label(text="推奨手順", icon='CHECKMARK')
        box.label(text="1. 基本ガイド生成")
        box.label(text="2. 配置点生成")
        box.label(text="3. 必要なら配置点調整")
        box.label(text="4. カーブ毛束生成")
        box.label(text="5. カーブ編集 / 根元集中チェック")
        box = layout.box()
        box.label(text="カーブ形状について", icon='OUTLINER_OB_CURVE')
        box.label(text="生成直後は円柱状に見える場合があります。")
        box.label(text="共有テーパーで毛先を細くします。")
        box.label(text="1. プリセットを選ぶ")
        box.label(text="2. プリセットを反映")
        box.label(text="3. テーパー形状を作成/更新")
        box.label(text="4. 選択または全カーブへ適用")
        box.label(text="自動適用ONなら新規カーブにも反映されます。")
        box = layout.box()
        box.label(text="三つ編みについて", icon='OUTLINER_OB_CURVE')
        box.label(text="1本の制御カーブを編集します。")
        box.label(text="表示用三つ編みは更新ボタンで再生成します。")
        box.label(text="通常カーブ用テーパーとは別管理です。")
        box = layout.box()
        box.label(text="配置点について", icon='MESH_UVSPHERE')
        box.label(text="現在の基本ガイド位置を参照します。")
        box.label(text="基本ガイド移動後は「配置点を生成/更新」を押してください。")
        box.label(text="配置点と警告は上書きされます。")
        box.label(text="既存のカーブ毛束は削除されません。")


classes = (
    HGD_PT_quick_start,
    HGD_PT_setup,
    HGD_PT_guide_lines,
    HGD_PT_regions,
    HGD_PT_placement,
    HGD_PT_curve_strand,
    HGD_PT_braid,
    HGD_PT_curve_shape,
    HGD_PT_curve_batch_adjust,
    HGD_PT_curve_follow,
    HGD_PT_side_mirror,
    HGD_PT_validation,
    HGD_PT_display_cleanup,
    HGD_PT_help,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

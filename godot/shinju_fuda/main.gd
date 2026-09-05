extends Control

const GOLD := Color("#f6c65b")
const INK := Color("#101729")
var player_hp := 100
var enemy_hp := 100
var turn := 0
var battle_started := false
var busy := false
var enemy_bar: ProgressBar
var player_bar: ProgressBar
var kohaku: TextureRect
var enemy: Control
var message: Label
var action_row: HBoxContainer
var summon_card: Button

func _ready() -> void:
	var app_theme := Theme.new()
	app_theme.default_font = load("res://assets/NotoSansJP-Variable.ttf")
	app_theme.default_font_size = 16
	theme = app_theme
	_build_screen()

func panel_style(color: Color, radius := 18, border := GOLD) -> StyleBoxFlat:
	var s := StyleBoxFlat.new()
	s.bg_color = color
	s.border_color = border
	s.set_border_width_all(2)
	s.set_corner_radius_all(radius)
	s.content_margin_left = 18
	s.content_margin_right = 18
	s.content_margin_top = 12
	s.content_margin_bottom = 12
	return s

func _label(text: String, size: int, color := Color.WHITE) -> Label:
	var l := Label.new()
	l.text = text
	l.add_theme_font_size_override("font_size", size)
	l.add_theme_color_override("font_color", color)
	l.add_theme_color_override("font_shadow_color", Color(0, 0, 0, .8))
	l.add_theme_constant_override("shadow_offset_x", 2)
	l.add_theme_constant_override("shadow_offset_y", 2)
	return l

func _build_screen() -> void:
	var bg := TextureRect.new()
	bg.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	bg.texture = load("res://assets/shrine_battle.png")
	bg.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	bg.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_COVERED
	add_child(bg)

	var shade := ColorRect.new()
	shade.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	shade.color = Color(0.02, 0.04, 0.10, .26)
	add_child(shade)

	var title := _label("神 獣 札", 29, GOLD)
	title.position = Vector2(20, 18)
	add_child(title)
	var chapter := _label("第一印　黄昏の社", 14, Color("#f4ead7"))
	chapter.position = Vector2(22, 57)
	add_child(chapter)

	_build_enemy()
	_build_player()
	_build_hud()

func _build_enemy() -> void:
	enemy = Control.new()
	enemy.position = Vector2(195, 105)
	enemy.size = Vector2(185, 210)
	add_child(enemy)
	var aura := Polygon2D.new()
	var points := PackedVector2Array()
	for i in 48:
		var a := TAU * i / 48.0
		points.append(Vector2(92, 104) + Vector2(cos(a) * 78, sin(a) * 78))
	aura.polygon = points
	aura.color = Color(0.32, 0.08, 0.55, .45)
	enemy.add_child(aura)
	var body := _label("影喰いの獏", 19, Color("#f0d9ff"))
	body.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	body.position = Vector2(8, 76)
	body.size = Vector2(170, 38)
	enemy.add_child(body)
	var eyes := _label("◉　◉", 25, Color("#ff6af2"))
	eyes.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	eyes.position = Vector2(25, 115)
	eyes.size = Vector2(135, 38)
	enemy.add_child(eyes)

func _build_player() -> void:
	kohaku = TextureRect.new()
	kohaku.texture = load("res://assets/kohaku.png")
	kohaku.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	kohaku.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	kohaku.position = Vector2(-10, 255)
	kohaku.size = Vector2(285, 285)
	kohaku.modulate.a = 0.0
	kohaku.scale = Vector2(.15, .15)
	kohaku.pivot_offset = kohaku.size / 2
	add_child(kohaku)

	summon_card = Button.new()
	summon_card.text = "神獣札\n炎狐 コハク"
	summon_card.position = Vector2(105, 245)
	summon_card.size = Vector2(180, 255)
	summon_card.add_theme_font_size_override("font_size", 21)
	summon_card.add_theme_color_override("font_color", Color("#38200e"))
	summon_card.add_theme_stylebox_override("normal", panel_style(Color("#f5e4b8"), 14, Color("#c98b31")))
	summon_card.add_theme_stylebox_override("hover", panel_style(Color("#fff2cb"), 14, Color("#fff0a1")))
	summon_card.pressed.connect(_summon)
	add_child(summon_card)

func _build_hud() -> void:
	var enemy_name := _label("禍獣　影喰いの獏　Lv.3", 14)
	enemy_name.position = Vector2(202, 82)
	add_child(enemy_name)
	enemy_bar = ProgressBar.new()
	enemy_bar.position = Vector2(202, 105)
	enemy_bar.size = Vector2(168, 13)
	enemy_bar.value = 100
	enemy_bar.show_percentage = false
	add_child(enemy_bar)

	var box := PanelContainer.new()
	box.position = Vector2(12, 630)
	box.size = Vector2(366, 196)
	box.add_theme_stylebox_override("panel", panel_style(Color(0.035, 0.055, 0.11, .92), 20))
	add_child(box)
	var v := VBoxContainer.new()
	box.add_child(v)
	message = _label("石版が震えている……\n札をタップして、コハクを呼び出そう。", 16, Color("#fff3d6"))
	message.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	message.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	message.custom_minimum_size = Vector2(320, 55)
	v.add_child(message)
	player_bar = ProgressBar.new()
	player_bar.value = 100
	player_bar.show_percentage = false
	player_bar.visible = false
	v.add_child(player_bar)
	action_row = HBoxContainer.new()
	action_row.alignment = BoxContainer.ALIGNMENT_CENTER
	action_row.add_theme_constant_override("separation", 7)
	action_row.visible = false
	v.add_child(action_row)
	for data in [["狐火", 24], ["印返し", 15], ["見切る", 0]]:
		var b := Button.new()
		b.text = data[0]
		b.custom_minimum_size = Vector2(105, 52)
		b.add_theme_font_size_override("font_size", 16)
		b.add_theme_stylebox_override("normal", panel_style(Color("#69331f"), 12, GOLD))
		b.pressed.connect(_act.bind(data[0], data[1]))
		action_row.add_child(b)

func _summon() -> void:
	if battle_started: return
	battle_started = true
	summon_card.disabled = true
	message.text = "札よ、結びを示せ——来い、コハク！"
	var tw := create_tween().set_parallel(true)
	tw.tween_property(summon_card, "scale", Vector2(.05, 1.25), .28).set_trans(Tween.TRANS_BACK)
	tw.tween_property(summon_card, "modulate:a", 0.0, .34)
	tw.tween_property(kohaku, "modulate:a", 1.0, .38).set_delay(.18)
	tw.tween_property(kohaku, "scale", Vector2.ONE, .55).set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT).set_delay(.18)
	await tw.finished
	summon_card.hide()
	action_row.visible = true
	player_bar.visible = true
	message.text = "相手は紫の気を溜めている。次の一手を選べ。"

func _act(move: String, damage: int) -> void:
	if busy or enemy_hp <= 0: return
	busy = true
	action_row.visible = false
	turn += 1
	if move == "見切る":
		message.text = "コハクは気配を読む……次の攻撃は『夢喰らい』だ！"
		await get_tree().create_timer(1.0).timeout
		player_hp = max(0, player_hp - 5)
	else:
		var bonus := 8 if move == "印返し" and turn % 2 == 0 else 0
		enemy_hp = max(0, enemy_hp - damage - bonus)
		enemy_bar.value = enemy_hp
		message.text = "コハクの「%s」！　禍獣の結界を %d 削った！" % [move, damage + bonus]
		var tw := create_tween()
		tw.tween_property(kohaku, "position:x", 35.0, .14)
		tw.tween_property(kohaku, "position:x", -10.0, .22).set_trans(Tween.TRANS_BACK)
		await tw.finished
	if enemy_hp <= 0:
		message.text = "契りの刻！ 禍獣の心に触れ、白紙の札へ迎えよう。"
		await get_tree().create_timer(.8).timeout
		var contract := Button.new()
		contract.text = "神獣契約を結ぶ"
		contract.custom_minimum_size = Vector2(250, 52)
		contract.add_theme_font_size_override("font_size", 18)
		contract.add_theme_stylebox_override("normal", panel_style(Color("#8b561d"), 12, Color("#ffe8a2")))
		action_row.add_child(contract)
		action_row.visible = true
		contract.pressed.connect(_contract)
		busy = false
		return
	await get_tree().create_timer(.65).timeout
	player_hp = max(0, player_hp - (12 if move != "見切る" else 5))
	player_bar.value = player_hp
	message.text = "影喰いの獏の反撃！ コハクはまだ戦える。"
	await get_tree().create_timer(.75).timeout
	action_row.visible = true
	message.text = "敵の気配が揺らいだ。どう指示する？"
	busy = false

func _contract() -> void:
	action_row.visible = false
	message.text = "新たな神獣札「夢獏 ムウ」を手に入れた！　——試作版クリア——"
	var tw := create_tween().set_parallel(true)
	tw.tween_property(enemy, "scale", Vector2(.05, .05), .55).set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_IN)
	tw.tween_property(enemy, "modulate:a", 0.0, .5)

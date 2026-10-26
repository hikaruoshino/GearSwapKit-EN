# -*- coding: utf-8 -*-
"""セットの一覧 (どういう状況のセットか) とヘルプ文。

path は GearSwap (Mote-Include) の sets.* の名前。language='japanese' で動かす前提で、
日本語のアビリティ名・スキル名をそのままキーにする。
verified=False のものは、キットのゲーム内確認がまだのもの (画面に「未確認」と出す)。
"""

# 共通 (どのジョブでも使える)
COMMON = [
    dict(path="sets.idle", title="待機", verified=True,
         help="戦闘していないとき (立っているだけ・移動中) に着る装備。HP・MP の回復、移動速度、被ダメージ軽減など、普段の装備を入れます。"),
    dict(path="sets.idle.DT", title="待機 (被ダメージ軽減)", verified=True,
         help="待機中に、被ダメージを減らしたいときの装備 (IdleMode を DT にしたとき)。物理・魔法ダメージ軽減 (DT) を重ねた装備を入れます。"),
    dict(path="sets.resting", title="休憩 (/heal)", verified=True,
         help="座って休んでいる (/heal) ときの装備。リフレッシュ・リジェネなど、MP と HP の回復を入れます。"),
    dict(path="sets.engaged", title="戦闘中 (通常)", verified=True,
         help="敵と戦っている (戦闘態勢) ときの基本の装備。命中・攻撃・ストアTP・ダブルアタックなど、普段の攻撃用の装備を入れます。"),
    dict(path="sets.engaged.DT", title="戦闘中 (被ダメージ軽減)", verified=True,
         help="戦闘中に、被ダメージを減らしたいときの装備 (//gs c cycle HybridMode で DT にしたとき)。"
              "物理・魔法ダメージ軽減 (DT) を重ねた、カットの装備を入れます。"),
    dict(path="sets.precast.FC", title="詠唱の開始 (ファストキャスト)", verified=True,
         help="魔法を唱え始めるときの装備。ファストキャスト (詠唱時間短縮) を重ねます。詠唱が短くなる代わりに、効果の装備は次の「詠唱中」の装備で着ます。"),
    dict(path="sets.precast.WS", title="ウェポンスキル (共通)", verified=True,
         help="ウェポンスキルを使う瞬間の装備。WSダメージ・STR など、威力の装備を入れます。技ごとに変えたいときは、下の「技ごとの追加」で足します。"),
    dict(path="sets.defense.PDT", title="物理の被ダメージ軽減", verified=True,
         help="物理ダメージを減らしたいときに、上に重ねる装備 (DefenseMode を PDT にしたとき)。"),
    dict(path="sets.defense.MDT", title="魔法の被ダメージ軽減", verified=True,
         help="魔法ダメージを減らしたいときに、上に重ねる装備 (DefenseMode を MDT にしたとき)。"),
    dict(path="sets.Kiting", title="移動速度アップ", verified=True,
         help="移動を速くしたいとき (Kiting をオン) に、上に重ねる装備。移動速度アップの靴などを入れます。"),
]

MAGIC_SKILLS = [
    ("回復魔法", "ケアルなどの回復魔法を唱えている間の装備。回復量アップ・詠唱中断率ダウンなどを入れます。"),
    ("強化魔法", "ヘイスト・プロテスなどの強化魔法を唱えている間の装備。強化魔法スキル・効果時間アップなどを入れます。"),
    ("弱体魔法", "スロウ・スリプルなどの弱体魔法を唱えている間の装備。魔法命中・弱体魔法スキルなどを入れます。"),
    ("精霊魔法", "ファイアなどの精霊魔法を唱えている間の装備。魔法攻撃力・魔法ダメージなど、威力の装備を入れます。"),
    ("暗黒魔法", "ドレインなどの暗黒魔法を唱えている間の装備。暗黒魔法スキルなどを入れます。"),
]

import ws_types as WS

# ジョブ別の追加 (未対応ジョブ中心)
JOB = {
    "SMN": [
        dict(path="sets.idle.Avatar", title="待機 (召喚獣がいるとき = 維持費)", verified=True,
             help="召喚獣を呼び出している間の待機装備。召喚獣の維持費の軽減・リフレッシュなどを入れます。ペットがいないときは、上の「待機」の装備になります。"),
        dict(path="sets.precast.BloodPactWard", title="履行の短縮", verified=True,
             help="契約の履行を使う瞬間の装備。契約の履行の再使用時間短縮 (履行間隔短縮・履行間隔短縮II) を入れます。"
                  "幻術 (攻撃) の履行も、験術 (強化・弱体) の履行も、この装備で使います。使ったあと、召喚獣が実行するときに下の履行の装備に替わります。"),
        dict(path="sets.SmnSkill", title="召喚魔法スキル", verified=True,
             help="召喚魔法スキルを上げる装備。強化の履行 (ヘイスガ・灼熱の咆哮など) は、この装備で実行します。"),
        dict(path="sets.midcast.Pet.AvatarPhysicalPacts", title="物理の履行", verified=True,
             help="物理の契約の履行 (プレデタークロー・ボルトストライク・ラッシュなど) を召喚獣が実行している間の装備。"
                  "ペットの攻撃力・命中・契約の履行ダメージなどを入れます。どの履行が物理かは、キットが知っています (FF11 用語辞典で確認)。"),
        dict(path="sets.midcast.Pet.AvatarMagicalPacts", title="魔法の履行", verified=True,
             help="魔法の契約の履行 (メテオストライク・ヘヴンリーストライク・グランドフォールなど、属性の技) を召喚獣が実行している間の装備。"
                  "ペットの魔法攻撃力・魔命・契約の履行ダメージなどを入れます。"),
        dict(path="sets.midcast.Pet.AvatarBuffWard", title="強化の履行", verified=True,
             help="強化・回復の履行 (ヘイスガ・灼熱の咆哮・ルビーの癒しなど) を召喚獣が実行している間の装備。"
                  "作らなければ「召喚魔法スキル」の装備を使います (強化の履行は召喚魔法スキルで効果が上がるため)。"),
        dict(path="sets.midcast.Pet.AvatarDeBuffWard", title="弱体の履行", verified=True,
             help="弱体の履行 (スリプガ・スロウガ・タイダルロアなど) を召喚獣が実行している間の装備。ペットの魔命などを入れます。"),
    ],
    "BLU": [
        dict(path="sets.midcast['青魔法']", title="青魔法 (共通)", verified=False,
             help="青魔法を唱えている間の装備。青魔法スキル・魔法命中などを入れます。魔法ごとに変えたいときは、下の「技ごとの追加」で足します。"),
    ],
    "PUP": [
        dict(path="sets.idle.Pet", title="待機 (オートマトンがいるとき = マトンSTP)", verified=True,
             help="オートマトンを呼び出していて、自分は待機しているときの装備 (オートマトンだけを戦わせるとき)。"
                  "オートマトンのストアTP・命中・攻撃などを入れます。ペットがいないときは、上の「待機」の装備になります。"),
        dict(path="sets.idle.Tate", title="待機 (マトン盾)", verified=True,
             help="オートマトンを盾にして、自分は待機しているときの装備 (//gs c cycle IdleMode で Tate にしたとき)。"
                  "オートマトンの被ダメージ軽減・敵対心・リジェネなどを入れます。"),
        dict(path="sets.engaged.Tate", title="戦闘中 (マトン盾)", verified=True,
             help="オートマトンを盾にして、自分も戦っているときの装備 (//gs c cycle OffenseMode で Tate にしたとき)。"
                  "「戦闘中 (通常)」は、オートマトンと一緒に殴る (共闘) ときの装備です。"),
        dict(path="sets.engaged.PetSTP", title="戦闘中 (マトンSTP)", verified=True,
             help="自分も戦闘態勢で、オートマトンの攻撃を重視するときの装備 (//gs c cycle OffenseMode で PetSTP にしたとき)。"
                  "オートマトンのストアTP・命中・攻撃などを入れます。"),
        dict(path="sets.midcast.Pet", title="オートマトンの技・魔法 (共通)", verified=False,
             help="オートマトンが行動している間の装備。パペットの能力アップなどを入れます。"),
        dict(path="sets.midcast.Pet.WeaponSkill", title="オートマトンの WS", verified=True,
             help="オートマトンがウェポンスキル (連携属性のある技: ボーンクラッシャー・アームズマッシャーなど) を出すときの装備。"
                  "ペットのWSダメージ・攻撃力・命中などを入れます。技が出たときに着ます。メイン (シュコアトルなど) も持ち替えます。"
                  "ただし乾坤圏を持っているときは替えません。メインが無ければ今の武器のまま。WS が終わったら、元の武器に戻します。下のチェックを入れると、オートマトンの TP が "
                  "930 以上になったら先に着ておきます (技が出てからでは着替えが間に合わないことがあるため)。"),
        dict(path="sets.midcast.Pet.Enmity", title="オートマトンの敵対心 (ストロボ・フラッシュバルブ)", verified=True,
             help="オートマトンがストロボ (挑発)・フラッシュバルブを出すときの装備。ペットの敵対心アップなどを入れます。"
                  "技が出たときに着ます。下のチェックを入れると、再使用まで残り 2 秒になったら先に着ておきます "
                  "(ストロボは火のマニューバ中、フラッシュバルブは光のマニューバ中で、そのアタッチメントを付けているとき)。"),
        dict(path="sets.precast.JA.Maneuver", title="マニューバを使う", verified=True,
             help="マニューバ (火・氷・風・土・雷・水・光・闇) を使う瞬間の装備。マニューバの効果時間アップなどを入れます。8 種類まとめて、この装備になります。"
                  "メイン (乾坤圏など) も、このセットのものに持ち替えます (武器を替えると TP は消えます)。"),
    ],
    "BST": [
        dict(path="sets.idle.Pet", title="待機 (ペットがいるとき = ペットのカット)", verified=False,
             help="ペットを連れている間の待機装備。ペットの被ダメージ軽減 (カット)・回復・ヘイストなどを入れます。ペットがいないときは、上の「待機」の装備になります。"),
        dict(path="sets.midcast.Pet", title="ペットの技 (共通)", verified=False,
             help="ペットが技を実行している間の装備。ペットの命中・魔命・ダメージ・TPボーナスなどを入れます。ほんきだせ系の技だけを別にしたいときは、次の項目を使います。"),
        dict(path="sets.midcast.Pet.PhysicalDamage", title="ペットの技 (物理: 命中・TPボーナス)", verified=False,
             help="ペットが物理の技 (フットキックなど) を出すときの装備。ペットの命中・攻撃力・TPボーナスなどを入れます。"
                  "どの技が物理かは、キットが知っています (FF11 用語辞典で確認)。"),
        dict(path="sets.midcast.Pet.MagicDamage", title="ペットの技 (魔法・弱体: 魔命)", verified=False,
             help="ペットが魔法の技 (ブレスなど) や弱体の技を出すときの装備。ペットの魔命・魔法攻撃力などを入れます。"),
        dict(path="sets.midcast.Pet.Monster", title="ペットの技 (ほんきだせ・しじをさせろ の技)", verified=False,
             help="ペットが、ほんきだせ・しじをさせろ で出す技 (フットキックなど) を実行している間の装備。ペットの命中・魔命・ペットの攻撃力・TPボーナスなどを入れます。技ごとに変えたいときは、下の「技ごとの追加」を使います。"),
        dict(path="sets.precast.JA['Sic']", alias="sets.precast.JA['ほんきだせ']", title="ほんきだせ を指示する", verified=False,
             help="ペットに「ほんきだせ」を指示する瞬間の装備。ほんきだせ・しじをさせろ の使用間隔短縮 (レディ・リキャスト) などを入れます。"),
        dict(path="sets.precast.JA['Ready']", alias="sets.precast.JA['しじをさせろ']", title="しじをさせろ を指示する", verified=False,
             help="ペットに「しじをさせろ」を指示する瞬間の装備。使用間隔短縮などを入れます。"),
    ],
    "PLD": [
        dict(path="sets.Enmity", title="敵対心", verified=True,
             help="敵対心を上げる装備。アビリティを使う瞬間 (セットを作っていないアビリティすべて) と、技ごとに足したアビリティ・"
                  "敵対心の魔法 (フラッシュ・フォイル・リアクト・クルセード・バニシュガなど) の土台になります。"),
        dict(path="sets.EnmityMax", title="敵対心 (最大)", verified=True,
             help="詠唱の無いアビリティ (センチネル・ランパート・マジェスティ・ヴァレション・ヴァリエンス・パリセード) で使う、"
                  "敵対心を最大まで上げる装備。作らなければ「敵対心」を使います。"),
        dict(path="sets.midcast.interruption", title="詠唱中断", verified=True,
             help="詠唱中に攻撃を受けても詠唱が止まらないようにする装備 (詠唱中断率ダウン)。セットを作っていない魔法は、詠唱中ずっとこの装備です。"
                  "下のチェックを入れると、ケアルやフラッシュでも 3 段階で着替えます (詠唱の開始 = ファストキャスト → 詠唱中 = 詠唱中断 → "
                  "着弾の直前 = ケアル・敵対心などの装備)。"),
        dict(path="sets.midcast.Cure", title="ケアル", verified=True,
             help="ケアル (I〜IV) の装備。ケアル回復量アップ・被ケアル回復量アップ・HP などを入れます。"),
        dict(path="sets.midcast.Flash", alias="sets.midcast['フラッシュ']", title="フラッシュ", verified=False,
             help="フラッシュの装備。「敵対心」に重ねて作ります。ほかの敵対心の魔法 (フォイル・リアクトなど) は、下の「技ごとの追加」で足すと、同じく「敵対心」に重ねます。"),
        dict(path="sets.idle.Magical", title="対魔法 (手動で切り替え)", verified=True,
             help="魔法の被ダメージを減らす装備 (魔法被ダメージ軽減・魔回避・魔防)。ゲームで「//gs c toggle Magical」を押すと、"
                  "待機と戦闘中の装備に重ねます。もう一度押すと外します。メインとサブ (マリグナスソード・イージスなど) も、このセットのものに持ち替えます"
                  "(武器を替えると TP は消えます)。オフにすると、武器の切り替えで選んでいる武器に戻します。"),
        dict(path="sets.StatusResist", title="状態異常耐性 (手動で切り替え)", verified=False,
             help="状態異常にかかりにくくする装備 (耐性・魔回避など)。ゲームで「//gs c toggle StatusResist」を押すと、"
                  "待機と戦闘中の装備に重ねます (対魔法と両方オンなら、こちらが上)。メインとサブも、このセットのものに持ち替えます。"),
    ],
    "NIN": [
        dict(path="sets.midcast['忍術']", title="忍術 (共通)", verified=False,
             help="忍術を唱えている間の装備。魔法命中・忍術スキルなどを入れます。術ごとに変えたいときは、下の「技ごとの追加」で足します。"),
        dict(path="sets.midcast.ElementalNinjutsu", title="攻撃の忍術 (火遁・氷遁など)", verified=False,
             help="火遁・氷遁・風遁・土遁・雷遁・水遁の術を唱えている間の装備。魔法攻撃力・魔法命中などを入れます。"),
        dict(path="sets.precast.FC.Utsusemi", title="空蝉の術 (詠唱の開始)", verified=False,
             help="空蝉の術 (壱・弐・参) を唱え始める装備。ファストキャストを重ねて、素早く唱えます。"),
        dict(path="sets.midcast.Utsusemi", title="空蝉の術 (詠唱中)", verified=False,
             help="空蝉の術を唱えている間の装備。詠唱中断率ダウンなどを入れます。"),
    ],
}

# 魔法のジョブの、技能ごとの魔法 (未対応ジョブ以外でも使える)
JOBS_WITH_SKILL_SETS = {"WHM", "RDM", "BLM", "SCH", "GEO", "PLD", "DRK", "RUN", "BRD", "SMN", "BLU", "NIN"}

ALL_JOBS = ["WAR", "MNK", "WHM", "BLM", "RDM", "THF", "PLD", "DRK", "BST", "BRD", "RNG", "SAM", "NIN", "DRG",
            "SMN", "BLU", "COR", "PUP", "DNC", "SCH", "GEO", "RUN"]

# 技ごとの追加 (自由に名前を足せる枠)
CUSTOM_KINDS = [
    ("sets.precast.WS", "ウェポンスキル", "技の名前を入れます (例: レデンサリュート)。日本語で入れると、英語名を自動で調べます。その技を使う瞬間だけ、この装備にします。"),
    ("sets.precast.JA", "ジョブアビリティ", "アビリティの名前を入れます (例: マナシード)。それを使う瞬間だけ、この装備にします。"),
    ("sets.midcast", "魔法", "魔法の名前を入れます (例: ケアルIV)。その魔法を唱えている間だけ、この装備にします。"),
    ("sets.midcast.Pet", "ペットの技", "召喚獣・ペットの技の名前を入れます (例: ボルトストライク)。その技を実行している間だけ、この装備にします。"),
    ("sets.midcast", "被強化の装備", "ほかの人 (や自分) から受けるファランクス・プロテス・シェルを強くする装備です (シェルターリングなど)。"
     "自分に向けて唱え始められたら着て、届いたら元の装備に戻します。"),
]

# 被強化の装備 (技ごとの追加の「被強化の装備」で選ぶ)。セットの名前・日本語名・対象の魔法 (res の番号)・範囲の魔法
RECEIVED = [
    ("IncreasedPhalanx", "被ファランクス (受けるファランクスの強化)", [106, 107], []),
    ("IncreasedProtect", "被プロテス (受けるプロテスの強化)", [43, 44, 45, 46, 47], [125, 126, 127, 128, 129]),
    ("IncreasedShell", "被シェル (受けるシェルの強化)", [48, 49, 50, 51, 52], [130, 131, 132, 133, 134]),
]
RECEIVED_HELP = ("ほかの人 (や自分) から受ける魔法を強くする装備です。自分に向けて唱え始められたら着て、魔法が届いたら (または 8 秒で) "
                 "元の装備に戻します。範囲の魔法 (プロテア・シェルラ・学者の女神降臨の章のあとのファランクス) は、"
                 "パーティーの人が唱えたときに着ます。自分で自分に唱えるときは、詠唱中に着ます。")


# 武器の切り替え (装備のセットとは別。//gs c cycle MainWeapons などで、武器を順番に持ち替える)
WEAPON_ENTRIES = [
    dict(path="weapons:main", weapon_slot="main", title="武器の切り替え (メイン)", verified=True,
         help="メインの武器を、順番に持ち替えられるようにします。ゲームでは「//gs c cycle MainWeapons」を押すたびに、次の武器に替わります。使いたい武器を 1 本ずつ装備して、//gs export で書き出し、ここへ「export から武器を足す」で追加してください。武器は、装備のセット (待機・戦闘中など) には入れません。持ち替えても、TP が消えるのは、武器を替えたときだけです。"),
    dict(path="weapons:sub", weapon_slot="sub", title="武器の切り替え (サブ)", verified=True,
         help="サブ (盾・もう片方の武器・グリップ) を、順番に持ち替えられるようにします。ゲームでは「//gs c cycle SubWeapons」で切り替えます。追加のしかたは、メインと同じです。両手武器のときは、サブを装備できないので、気をつけてください。"),
    dict(path="weapons:range", weapon_slot="range", title="武器の切り替え (遠隔)", verified=True,
         help="遠隔の武器 (弓・銃・楽器など) を、順番に持ち替えられるようにします。ゲームでは「//gs c cycle RangeWeapons」で切り替えます。追加のしかたは、メインと同じです。"),
]


# 矢弾の使い分け (狩人・コルセアだけ)。所持品の一覧 (//gs export all) から選ぶ
AMMO_HELP_TAIL = ("「所持品の一覧から選ぶ…」で、//gs export all の一覧から選んでください (装備して //gs export したファイルを「export から矢弾を選ぶ…」で使うこともできます)。"
                  "矢弾を選ぶと、ほかのセットの export に入っている矢弾は使わず、ここで選んだ弾を場面に合わせて装備します。")
AMMO_ENTRIES = [
    dict(path="ammo:physical", ammo_role="physical", title="矢弾 (物理)", verified=True,
         help="遠隔攻撃と、物理の遠隔 WS (ラストスタンドなど) で使う矢弾です。特殊弾を使ったあとも、この弾に戻します。"
              "1 つだけ選べます (選び直すと置き換わります)。" + AMMO_HELP_TAIL),
    dict(path="ammo:magical", ammo_role="magical", title="矢弾 (魔攻)", verified=True,
         help="魔法属性の遠隔 WS (レデンサリュート・ワイルドファイア・トゥルーフライトなど) で使う矢弾です。"
              "選ばなければ、物理の弾を使います。1 つだけ選べます。" + AMMO_HELP_TAIL),
    dict(path="ammo:quickdraw", ammo_role="quickdraw", title="矢弾 (クイックドロー)", verified=True, jobs=("COR",),
         help="クイックドローで使う弾です (アニミキーブレットなど)。使い終わったら物理の弾に戻すので、遠隔攻撃で撃ってしまいません。"
              "1 つだけ選べます。" + AMMO_HELP_TAIL),
    dict(path="ammo:special", ammo_role="special", title="矢弾 (特殊弾・WS ごと)", verified=True,
         help="決まった WS だけで使う弾です (例: イオリアンエッジ・サベッジブレードにホクスボクブレット)。"
              "弾を選んだあと、その弾を使う WS を選びます。WS の瞬間だけ着て、終わったら物理の弾に戻します (誤射防止)。"
              "同じ WS に別の弾を選ぶと置き換わります。" + AMMO_HELP_TAIL),
]


WS_MAGIC_ENTRY = dict(
    path="sets.precast.WS.Magic", title="ウェポンスキル (魔攻・属性物理)", verified=True,
    help="魔法属性のウェポンスキル (サンギンブレード・イオリアンエッジ・レデンサリュートなど、属性物理を含む) を使う瞬間の装備。"
         "魔法攻撃力・魔法ダメージ・WSダメージなどを入れます。どの WS が魔法属性かは、キットが知っています。"
         "技ごとに足した魔法属性の WS は、このセットに重ねて (set_combine) 作ります。"
         "狩人・コルセアで「ウェポンスキル (遠隔魔攻)」を作ったときは、遠隔の魔法属性 WS はそちらを使います。")
WS_CRIT_ENTRY = dict(
    path="sets.precast.WS.Critical", title="ウェポンスキル (クリティカル)", verified=False,
    help="クリティカルの出やすさで威力が変わるウェポンスキル (エヴィサレーション・ボーパルブレード・ランページ・迅など) を使う瞬間の装備。"
         "クリティカルヒット率・クリティカルダメージ・DEX などを入れます。どの WS がクリティカルかは、キットが知っています。"
         "技ごとに足したクリティカルの WS は、このセットに重ねて作ります。")
WS_RANGE_MAGIC_ENTRY = dict(
    path="sets.precast.WS.RangeMagic", title="ウェポンスキル (遠隔魔攻)", verified=True,
    help="魔法属性の遠隔ウェポンスキル (レデンサリュート・ワイルドファイア・トゥルーフライトなど) を使う瞬間の装備。"
         "魔法攻撃力・魔法ダメージ・飛命などを入れます。このセットを作らなければ、「ウェポンスキル (魔攻・属性物理)」を使います。"
         "技ごとに足した遠隔の魔法属性 WS は、このセットに重ねて作ります。")
WS_RANGE_ENTRY = dict(
    path="sets.precast.WS.Range", title="ウェポンスキル (遠隔・物理)", verified=True,
    help="弓術・射撃の物理ウェポンスキル (ジシュヌの光輝・ラストスタンドなど) を使う瞬間の装備。飛攻・飛命・WSダメージなどを入れます。"
         "レデンサリュートなど魔法属性の遠隔 WS は「ウェポンスキル (魔攻・属性物理)」を使います。")


# 遠隔攻撃 (狩人・コルセア)。sets.RA_STP・sets.RA_ACC は、作者の COR_gear.lua と同じ名前 (generator が sets.midcast.RA に結ぶ)
RANGED_ENTRIES = [
    dict(path="sets.precast.RA", title="遠隔の構え (スナップショット)", verified=False,
         help="遠隔攻撃を構える瞬間の装備。スナップショット・ラピッドショットなど、構えを速くする装備を入れます。"),
    dict(path="sets.RA_STP", title="遠隔攻撃 (STP)", verified=False,
         help="遠隔攻撃を撃っている間の基本の装備 (sets.midcast.RA)。ストアTP・飛攻・飛命などを入れます。"),
    dict(path="sets.RA_ACC", title="遠隔攻撃 (飛命)", verified=False,
         help="飛命を重視するときの遠隔攻撃の装備 (//gs c cycle RangedMode で Acc にしたとき。sets.midcast.RA.Acc)。"),
]

# コルセアのロールとクイックドロー。名前は作者の COR_gear.lua と同じ
COR_QD_MODES = [("sets.RA_QDSTP", "ソーティ", "StoreTP"), ("sets.RA_QDDPS", "通常", "Damage")]
COR_ENTRIES = [
    dict(path="sets.CorsairRoll", title="ロール (共通)", verified=False,
         help="ファントムロールを使う瞬間の装備 (sets.precast.CorsairRoll)。ロールの効果範囲・効果時間アップ・再使用短縮などを入れます。"
              "ロールごとの装備 (ＣＳトリコルヌ+3 でプリッツアロールなど) は、この装備に重ねて作ります。"),
    dict(path="sets.RA_QDSTP", title="クイックドロー (STP)", verified=False,
         help="クイックドローを撃つ瞬間の、ストアTP を重視した装備 (ソーティなど)。クイックドロー能力・ストアTP などを入れます。"
              "「クイックドロー (威力)」も作ると、//gs c cycle QuickDrawMode で切り替えます (ソーティ / 通常)。"),
    dict(path="sets.RA_QDDPS", title="クイックドロー (威力)", verified=False,
         help="クイックドローの威力を重視した装備。魔法攻撃力・クイックドロー能力・AGI などを入れます。"
              "//gs c cycle QuickDrawMode を「通常」にしたときに着ます。"),
    dict(path="sets.RA_QDACC", title="クイックドロー (魔命: ライト・ダーク)", verified=False,
         help="ライトショット・ダークショット (弱体を伸ばす・魔命が大事な弾) を撃つ瞬間の装備。魔法命中を重視します。"
              "この 2 つは、QuickDrawMode にかかわらず、この装備で撃ちます。"),
]
JOB["COR"] = COR_ENTRIES

# 魔法の系統のセット (Mote-Include が魔法の系統名 = spellMap で自動で探すもの)。ジョブごとに、使える系統だけ出す
SPELL_FAMILY_ENTRIES = {
    "sets.midcast.Cure": dict(title="ケアル", verified=False,
                              help="ケアル (I〜VI) を唱えている間の装備。ケアル回復量アップ・MND・回復魔法スキルなどを入れます。"
                                   "作らなければ「詠唱中 (回復魔法)」を使います。"),
    "sets.precast.FC.Cure": dict(title="詠唱の開始 (ケアル)", verified=False,
                                 help="ケアルを唱え始めるときの装備。ケアル詠唱時間短縮 (ケアル専用のファストキャスト) を重ねます。"
                                      "作らなければ「詠唱の開始 (ファストキャスト)」を使います。"),
    "sets.midcast.Regen": dict(title="リジェネ", verified=False,
                               help="リジェネ (I〜V) を唱えている間の装備。リジェネ効果アップ・効果時間アップなどを入れます。"),
    "sets.midcast.Refresh": dict(title="リフレシュ", verified=False,
                                 help="リフレシュ (I〜III) を唱えている間の装備。リフレシュ効果アップ・効果時間アップなどを入れます。"),
    "sets.midcast.Drain": dict(title="ドレイン・アスピル", verified=False,
                               help="ドレイン・アスピルを唱えている間の装備。ドレイン・アスピル吸収量アップ・暗黒魔法スキル・魔命などを入れます。"),
    "sets.midcast.Helix": dict(title="計略 (門の計)", verified=False,
                               help="火門の計などの計略を唱えている間の装備。魔法攻撃力・魔法ダメージなどを入れます (計略は精霊魔法と違う装備が合うことがあります)。"),
    "sets.midcast.ElementalEnfeeble": dict(title="属性の弱体 (バーン・ショックなど)", verified=False,
                                           help="バーン・フロスト・チョーク・ラスプ・ショック・ドラウンを唱えている間の装備。魔法命中・INT などを入れます。"),
}
SPELL_FAMILY_JOBS = {
    "sets.midcast.Cure": ("WHM", "RDM", "SCH", "BLU", "GEO", "SMN", "RUN"),
    "sets.precast.FC.Cure": ("WHM", "RDM", "SCH", "BLU", "GEO", "SMN", "RUN", "PLD"),
    "sets.midcast.Regen": ("WHM", "SCH", "RUN"),
    "sets.midcast.Refresh": ("RDM", "SCH", "RUN"),
    "sets.midcast.Drain": ("BLM", "SCH", "DRK", "GEO"),
    "sets.midcast.Helix": ("SCH",),
    "sets.midcast.ElementalEnfeeble": ("BLM",),
}
for _path, _e in SPELL_FAMILY_ENTRIES.items():
    _e["path"] = _path

# 神聖魔法・風水魔法 (技能で探すセット。ジョブを絞る)
JOB_SKILL_EXTRA = {"WHM": ["神聖魔法"], "PLD": ["神聖魔法"], "GEO": ["風水魔法"]}
SKILL_EXTRA_HELP = {
    "神聖魔法": "バニシュ・ホーリーなどの神聖魔法を唱えている間の装備。MND・魔法攻撃力・神聖魔法スキルなどを入れます。",
    "風水魔法": "インデ・ジオ (風水魔法) を唱えている間の装備。風水魔法スキル・羅盤の効果アップなどを入れます。",
}

# 踊り子 (Mote-Include はアビリティの種類 = spell.type で探す: sets.precast.Waltz など)
JOB["DNC"] = [
    dict(path="sets.precast.Waltz", title="ワルツ", verified=False,
         help="ケアルワルツなどワルツを使う瞬間の装備。ワルツ回復量アップ・CHR・ワルツの再使用短縮などを入れます。"),
    dict(path="sets.precast.Samba", title="サンバ", verified=False,
         help="サンバを使う瞬間の装備。サンバの効果時間アップなどを入れます。"),
    dict(path="sets.precast.Jig", title="ジグ", verified=False,
         help="ジグ (スペクトラルジグなど) を使う瞬間の装備。ジグの効果時間アップなどを入れます。"),
    dict(path="sets.precast.Step", title="ステップ", verified=False,
         help="ステップを使う瞬間の装備。命中 (ステップが外れないように) などを入れます。"),
    dict(path="sets.precast.Flourish1", title="フラリッシュ (I: バイオレントフラリッシュなど)", verified=False,
         help="フラリッシュIの技 (アニマススフラリッシュ・バイオレントフラリッシュなど) を使う瞬間の装備。魔法命中・命中などを入れます。"),
]


# --- 1.1.0 で足したセット (作者の *_gear.lua の見直し) ---
ALL = tuple(ALL_JOBS)
DUAL_JOBS = ("WAR", "MNK", "RDM", "THF", "DRK", "BST", "BRD", "SAM", "NIN", "DRG", "BLU", "COR", "DNC", "RUN")
# (ジョブ, 項目)。ジョブは ALL か、略称のタプル
EXTRA_ENTRIES = [
    (ALL, dict(path="sets.TreasureHunter", title="トレジャーハンター (手動で切り替え)", verified=False,
               help="トレジャーハンターの装備。ゲームで「//gs c toggle TreasureHunter」を押すと、戦闘中の装備に重ねます (待機には重ねません)。"
                    "敵に最初の一撃を入れたら、もう一度押して外してください。")),
    (DUAL_JOBS, dict(path="sets.engaged.dual11", title="二刀流 (サポ忍)", verified=False,
                     help="サポ忍のときに、戦闘中の装備に重ねる装備 (二刀流の値を合わせる耳・腰など)。サポジョブを見て、自動で重ねます。")),
    (DUAL_JOBS, dict(path="sets.engaged.dual21", title="二刀流 (サポ踊)", verified=False,
                     help="サポ踊のときに、戦闘中の装備に重ねる装備。サポジョブを見て、自動で重ねます。")),
    (("BLM", "RDM", "SCH", "GEO"),
     dict(path="sets.midcast['精霊魔法'].MB", title="詠唱中 (精霊魔法・マジックバースト)", verified=False,
          help="マジックバーストを狙うときの精霊魔法の装備。マジックバーストダメージ・魔法攻撃力などを入れます。"
               "「詠唱中 (精霊魔法)」に重ねて作ります。ゲームで「//gs c cycle CastingMode」で MB にしたときに着ます。")),
    (("MNK", "WHM", "BLM", "RDM", "PLD", "BRD", "RNG", "SMN", "BLU", "PUP", "SCH", "GEO", "RUN"),
     dict(path="sets.idle.Refresh", title="待機 (リフレシュ)", verified=False,
          help="MP を回復したいときの待機の装備 (リフレシュ)。ゲームで「//gs c cycle IdleMode」で Refresh にしたときに着ます。")),
    (ALL, dict(path="sets.engaged.Acc", title="戦闘中 (命中重視)", verified=False,
               help="命中が足りないときの戦闘中の装備。ゲームで「//gs c cycle OffenseMode」で Acc にしたときに着ます。")),
    (ALL, dict(path="sets.engaged.SubtleBlow", title="戦闘中 (モクシャ)", verified=False,
               help="敵に TP を与えにくくする装備 (モクシャ)。ゲームで「//gs c cycle OffenseMode」で SubtleBlow にしたときに着ます。")),
    (("BRD",), dict(path="sets.precast.FC['歌唱']", title="詠唱の開始 (歌)", verified=False,
                    help="歌を歌い始めるときの装備。歌唱詠唱時間短縮・ファストキャストを入れます。")),
]
SONG_FAMILIES = [
    ("March", "マーチ", "マーチ効果アップ・歌唱スキルなどを入れます。"),
    ("Minuet", "メヌエット", "メヌエット効果アップなどを入れます。"),
    ("Madrigal", "マドリガル", "マドリガル効果アップなどを入れます。"),
    ("Ballad", "バラード", "バラード効果アップなどを入れます。"),
    ("Minne", "ミンネ", "ミンネ効果アップなどを入れます。"),
    ("Paeon", "ピーアン", "ピーアン効果アップなどを入れます。"),
    ("Etude", "エチュード", "エチュード効果アップなどを入れます。"),
    ("Carol", "カロル", "カロル効果アップなどを入れます。"),
    ("Prelude", "プレリュード", "プレリュード効果アップなどを入れます。"),
    ("Mambo", "マンボ", "マンボ効果アップなどを入れます。"),
    ("Lullaby", "ララバイ", "魔法命中・歌唱スキル・効果時間などを入れます。"),
    ("Threnody", "スレノディ", "魔法命中・スレノディ効果アップなどを入れます。"),
    ("Elegy", "エレジー", "魔法命中・歌唱スキルなどを入れます。"),
    ("Requiem", "レクイエム", "魔法命中・歌唱スキルなどを入れます。"),
]
EXTRA_ENTRIES += [(("BRD",), dict(path="sets.midcast.%s" % fam, title="歌 (%s)" % ja, verified=False,
                                  help="%sを歌っている間の装備。%s" % (ja, why)))
                  for fam, ja, why in SONG_FAMILIES]
EXTRA_ENTRIES += [
    (("BLU",), dict(path="sets.midcast.BluePhysical", title="青魔法 (物理)", verified=False,
                    help="物理の青魔法 (シンカードリルなど) を唱えている間の装備。STR・DEX・命中・攻撃などを入れます。どの魔法が物理かは、キットが知っています。")),
    (("BLU",), dict(path="sets.midcast.BlueMagical", title="青魔法 (魔法)", verified=False,
                    help="魔法の青魔法 (アンビルライトニング・テネブラルクラッシュなど) を唱えている間の装備。魔法攻撃力・INT・魔法命中などを入れます。")),
    (("BLU",), dict(path="sets.midcast.BlueBuff", title="青魔法 (強化)", verified=False,
                    help="強化の青魔法 (コクーン・エラチックフラッターなど) を唱えている間の装備。青魔法スキル・効果時間などを入れます。")),
    (("BLU",), dict(path="sets.midcast.BlueHealing", title="青魔法 (回復)", verified=False,
                    help="回復の青魔法 (マジックフルーツ・ホワイトウインドなど) を唱えている間の装備。ケアル回復量・MND・VIT などを入れます。")),
    (("GEO",), dict(path="sets.idle.Luopan", title="待機 (羅盤がいるとき)", verified=False,
                    help="羅盤を出している間の待機の装備。羅盤の被ダメージ軽減・羅盤のリジェネなどを入れます。羅盤がいないときは、上の「待機」の装備になります。")),
    (("GEO",), dict(path="sets.midcast.Entrust", title="エントラスト中のインデ", verified=False,
                    help="エントラストを使ったあと、ほかの人にインデ魔法をかける間の装備。インデの効果時間アップなどを入れます。")),
]


BAR_ELEMENT_ENTRY = dict(
    path="sets.midcast.BarElement", title="詠唱中 (バ系の魔法)", verified=False,
    help="バファイア・バファイラなど、属性のバ系の魔法を唱えている間の装備。バ系効果アップ (シェダルサラウィルなど) を入れます。"
         "「詠唱中 (強化魔法)」に重ねて作るので、変えたい部位だけでかまいません。")


def sets_for_job(job):
    """そのジョブで選べるセットの一覧 (表示順)。"""
    out = []
    for e in COMMON:
        out.append(e)
        if e["path"] == "sets.precast.WS":
            # 共通の WS のすぐ後に、魔攻の WS と (遠隔武器が主のジョブだけ) 遠隔の WS
            out.append(WS_MAGIC_ENTRY)
            out.append(WS_CRIT_ENTRY)
            if job in WS.RANGED_SET_JOBS:
                out.append(WS_RANGE_ENTRY)
            if job in WS.RANGED_JOBS:
                out.append(WS_RANGE_MAGIC_ENTRY)
    out += WEAPON_ENTRIES
    if job in WS.RANGED_SET_JOBS:
        out += RANGED_ENTRIES
    if job in WS.RANGED_JOBS:
        out += [e for e in AMMO_ENTRIES if job in e.get("jobs", (job,))]
    out += JOB.get(job, [])
    have = {e["path"] for e in out}
    out += [e for p, e in SPELL_FAMILY_ENTRIES.items() if job in SPELL_FAMILY_JOBS[p] and p not in have]
    out += [e for jobs, e in EXTRA_ENTRIES if job in jobs and e["path"] not in have]
    if job in JOBS_WITH_SKILL_SETS:
        for skill, text in MAGIC_SKILLS + [(s, SKILL_EXTRA_HELP[s]) for s in JOB_SKILL_EXTRA.get(job, [])]:
            path = "sets.midcast['%s']" % skill
            if any(s["path"] == path for s in out):
                continue
            out.append(dict(path=path, title="詠唱中 (%s)" % skill, verified=False, help=text,  # noqa
                            title_en="Midcast (%s)" % SKILL_EN.get(skill, skill),
                            help_en=MAGIC_SKILLS_HELP_EN.get(skill, "")))
        out.append(BAR_ELEMENT_ENTRY)
    return out


# ---------------------------------------------------------------------------
# 英語 (i18n.L で切り替え)。path は変えない。各 dict に title_en / help_en を足す
# ---------------------------------------------------------------------------
from i18n import L, SKILL_EN  # noqa: E402

MAGIC_SKILLS_HELP_EN = {
    "回復魔法": "Gear worn while casting healing spells such as Cure. Cure potency, spell interruption rate -, etc.",
    "強化魔法": "Gear worn while casting enhancing spells such as Haste and Protect. Enhancing Magic skill, enhancing duration +, etc.",
    "弱体魔法": "Gear worn while casting enfeebles such as Slow and Sleep. Magic Accuracy, Enfeebling Magic skill, etc.",
    "精霊魔法": "Gear worn while casting elemental nukes such as Fire. Magic Attack, Magic Damage and other potency stats.",
    "暗黒魔法": "Gear worn while casting dark spells such as Drain. Dark Magic skill, etc.",
    "神聖魔法": "Gear worn while casting divine spells such as Banish and Holy. MND, Magic Attack, Divine Magic skill, etc.",
    "風水魔法": "Gear worn while casting Indi- and Geo- spells. Geomancy skill, luopan potency and the like.",
}

AMMO_HELP_TAIL_EN = (" Use \"Pick from inventory…\" to choose from your //gs export all list (or equip it, run //gs export, "
                     "and use \"Pick ammo from export...\"). Once ammo is chosen here, ammo in your other sets' exports is ignored "
                     "and the kit equips the ammo chosen here to fit the situation.")

_EN = {
    "sets.idle": ("Idle", "Gear worn when you're not fighting (standing or moving). Put your everyday gear here: Refresh, Regen, movement speed, damage taken -."),
    "sets.idle.DT": ("Idle (DT)", "Idle gear for cutting damage taken (IdleMode set to DT). Stack physical and magic damage taken - (DT)."),
    "sets.resting": ("Resting (/heal)", "Gear worn while resting (/heal). Put HP/MP recovery here, such as Refresh and Regen."),
    "sets.engaged": ("Engaged (normal)", "Your base gear while engaged. Accuracy, Attack, Store TP, Double Attack and the like."),
    "sets.engaged.DT": ("Engaged (DT)", "Engaged gear for cutting damage taken (//gs c cycle HybridMode to DT). Stack physical and magic damage taken - (DT)."),
    "sets.precast.FC": ("Precast (Fast Cast)", "Gear worn when you start casting. Stack Fast Cast here; gear that boosts the spell itself goes in the midcast sets."),
    "sets.precast.WS": ("Weapon skill (default)", "Gear worn the moment you use a weapon skill: weapon skill damage, STR and other damage stats. For different gear on a specific weapon skill, add it below under \"Add per skill\"."),
    "sets.defense.PDT": ("Defense: PDT (physical)","Layered on top when you want to cut physical damage (DefenseMode set to PDT)."),
    "sets.defense.MDT": ("Defense: MDT (magic)","Layered on top when you want to cut magic damage (DefenseMode set to MDT)."),
    "sets.Kiting": ("Movement speed", "Layered on top when Kiting is on. Put movement speed gear (boots and such) here."),
    # SMN
    "sets.idle.Avatar": ("Idle (avatar out: perpetuation)", "Idle gear while an avatar is summoned: avatar perpetuation cost -, Refresh, etc. Without a pet, the regular Idle set is used."),
    "sets.precast.BloodPactWard": ("Blood Pact delay", "Gear worn the moment you use a Blood Pact: Blood Pact delay - and Blood Pact delay II -. Both Rage and Ward pacts use this set; when the avatar performs the pact, you swap to the pact gear below."),
    "sets.SmnSkill": ("Summoning Magic skill", "Gear that raises Summoning Magic skill. Buff pacts (Hastega, Crimson Howl, etc.) are performed in this set."),
    "sets.midcast.Pet.AvatarPhysicalPacts": ("Physical Blood Pacts", "Gear worn while your avatar performs a physical pact (Predator Claws, Volt Strike, Rush, etc.): pet Attack, Accuracy, Blood Pact damage. The kit already knows which pacts are physical."),
    "sets.midcast.Pet.AvatarMagicalPacts": ("Magical Blood Pacts", "Gear worn while your avatar performs a magical (elemental) pact (Meteor Strike, Heavenly Strike, Grand Fall, etc.): pet Magic Attack, Magic Accuracy, Blood Pact damage."),
    "sets.midcast.Pet.AvatarBuffWard": ("Buff Blood Pacts", "Gear worn while your avatar performs a buff or healing pact (Hastega, Crimson Howl, Healing Ruby, etc.). If left empty, the Summoning Magic skill set is used (these pacts scale with skill)."),
    "sets.midcast.Pet.AvatarDeBuffWard": ("Debuff Blood Pacts", "Gear worn while your avatar performs a debuff pact (Sleepga, Slowga, Tidal Roar, etc.): pet Magic Accuracy and the like."),
    # BLU
    "sets.midcast['青魔法']": ("Blue Magic (default)", "Gear worn while casting Blue Magic: Blue Magic skill, Magic Accuracy, etc. For different gear per spell, add it under \"Add per skill\"."),
    # PUP
    "PUP:sets.idle.Pet": ("Idle (automaton out: pet Store TP)", "Idle gear while your automaton is out and you stay back (letting it fight alone): automaton Store TP, Accuracy, Attack, etc. Without a pet, the regular Idle set is used."),
    "sets.idle.Tate": ("Idle (automaton tank)", "Idle gear while your automaton tanks (//gs c cycle IdleMode to Tate): automaton damage taken -, Enmity, Regen, etc."),
    "sets.engaged.Tate": ("Engaged (automaton tank)", "Engaged gear while your automaton tanks and you fight too (//gs c cycle OffenseMode to Tate). \"Engaged (normal)\" is for meleeing alongside your automaton."),
    "sets.engaged.PetSTP": ("Engaged (automaton Store TP)", "Engaged gear that favors your automaton's offense (//gs c cycle OffenseMode to PetSTP): automaton Store TP, Accuracy, Attack, etc."),
    "PUP:sets.midcast.Pet": ("Automaton actions (default)", "Gear worn while your automaton acts: automaton skill and ability bonuses, etc."),
    "sets.midcast.Pet.WeaponSkill": ("Automaton weapon skill", "Gear worn when your automaton uses a weapon skill (moves with a skillchain property, such as Bone Crusher or Armor Shatterer): pet weapon skill damage, Attack, Accuracy. Swapped in when the move goes off, including the main weapon (e.g. Xiucoatl), except while you hold Kenkonken. With no main in the set, your weapon stays; afterwards your weapon is put back. Tick the box below to equip it early once the automaton reaches 930 TP (swapping after the move starts can be too late)."),
    "sets.midcast.Pet.Enmity": ("Automaton enmity (Provoke / Flashbulb)", "Gear worn when your automaton uses Provoke (Strobe) or Flashbulb: pet Enmity +. Swapped in when the move goes off. Tick the box below to equip it 2 seconds before it's ready (Strobe under Fire Maneuver, Flashbulb under Light Maneuver, with that attachment installed)."),
    "sets.precast.JA.Maneuver": ("Maneuvers", "Gear worn the moment you use a maneuver (any of the eight). Maneuver duration +, etc.; all eight share this set. Your main weapon (e.g. Kenkonken) is swapped to this set's weapon too (changing weapons resets TP)."),
    # BST
    "BST:sets.idle.Pet": ("Idle (pet out: pet DT)", "Idle gear while you have a pet out: pet damage taken -, Regen, Haste, etc. Without a pet, the regular Idle set is used."),
    "BST:sets.midcast.Pet": ("Pet moves (default)", "Gear worn while your pet performs a move: pet Accuracy, Magic Accuracy, damage, TP Bonus. To give Sic/Ready moves their own set, use the entries below."),
    "sets.midcast.Pet.PhysicalDamage": ("Pet moves (physical: Acc / TP Bonus)", "Gear worn when your pet uses a physical move (Foot Kick, etc.): pet Accuracy, Attack, TP Bonus. The kit already knows which moves are physical."),
    "sets.midcast.Pet.MagicDamage": ("Pet moves (magical / debuff: M.Acc)", "Gear worn when your pet uses a magical move (breaths, etc.) or a debuff: pet Magic Accuracy, Magic Attack, etc."),
    "sets.midcast.Pet.Monster": ("Pet moves (Sic / Ready)", "Gear worn while your pet performs a move from Sic or Ready (Foot Kick, etc.): pet Accuracy, Magic Accuracy, Attack, TP Bonus. For different gear per move, add it under \"Add per skill\"."),
    "sets.precast.JA['Sic']": ("Sic", "Gear worn the moment you use Sic: Sic/Ready recast - and the like."),
    "sets.precast.JA['Ready']": ("Ready", "Gear worn the moment you use Ready: Ready recast - and the like."),
    # PLD
    "sets.Enmity": ("Enmity", "Enmity + gear. The base for job abilities with no set of their own, abilities you add per skill, and enmity spells (Flash, Foil, Reprisal, Crusade, Banishga, etc.)."),
    "sets.EnmityMax": ("Enmity (max)", "Maximum-enmity gear for instant abilities (Sentinel, Rampart, Majesty, Vallation, Valiance, Palisade). If left empty, the Enmity set is used."),
    "sets.midcast.interruption": ("Spell interruption", "Spell interruption rate - gear so taking hits doesn't break your cast. Spells without a set of their own stay in this set for the whole cast. Tick the box below to also swap in three stages for Cure and Flash (precast = Fast Cast -> midcast = interruption -> just before it lands = Cure / Enmity gear)."),
    "sets.midcast.Cure": ("Cure", "Gear for Cure I-IV: Cure potency, Cure potency received, HP, etc."),
    "sets.midcast.Flash": ("Flash", "Gear for Flash, built on top of Enmity. Other enmity spells (Foil, Reprisal, etc.) added under \"Add per skill\" are built on top of Enmity as well."),
    "sets.idle.Magical": ("Anti-magic (manual toggle)", "Gear that cuts magic damage (MDT, Magic Evasion, Magic Def. Bonus). Use //gs c toggle Magical in game to layer it over your idle and engaged sets; use it again to remove it. Main and sub (e.g. Malignance Sword, Aegis) are swapped to this set's weapons too (changing weapons resets TP). Turning it off puts back the weapon chosen in your weapon cycle."),
    "sets.StatusResist": ("Status resist (manual toggle)", "Gear that resists status ailments (resistances, Magic Evasion, etc.). Use //gs c toggle StatusResist in game to layer it over your idle and engaged sets (above Anti-magic if both are on). Main and sub are swapped to this set's weapons too."),
    # NIN
    "sets.midcast['忍術']": ("Ninjutsu (default)", "Gear worn while casting Ninjutsu: Magic Accuracy, Ninjutsu skill, etc. For different gear per spell, add it under \"Add per skill\"."),
    "sets.midcast.ElementalNinjutsu": ("Elemental Ninjutsu (Katon, Hyoton...)", "Gear worn while casting Katon, Hyoton, Huton, Doton, Raiton or Suiton: Magic Attack, Magic Accuracy, etc."),
    "sets.precast.FC.Utsusemi": ("Utsusemi (precast)", "Gear worn when you start casting Utsusemi (Ichi, Ni, San). Stack Fast Cast to get it off quickly."),
    "sets.midcast.Utsusemi": ("Utsusemi (midcast)", "Gear worn while casting Utsusemi: spell interruption rate -, etc."),
    # weapon cycle
    "weapons:main": ("Weapon cycle (main)", "Lets you cycle through main weapons. In game, each //gs c cycle MainWeapons switches to the next one. Equip each weapon, run //gs export, and add it here with \"Add weapons from export\". Weapons don't go in the gear sets (idle, engaged, etc.); TP is lost only when the weapon actually changes."),
    "weapons:sub": ("Weapon cycle (sub)", "Lets you cycle through sub-slot items (shield, off-hand weapon, grip). In game, switch with //gs c cycle SubWeapons. Add them the same way as main. Two-handed weapons can't use a sub, so watch out."),
    "weapons:range": ("Weapon cycle (ranged)", "Lets you cycle through ranged weapons (bows, guns, instruments, etc.). In game, switch with //gs c cycle RangeWeapons. Add them the same way as main."),
    # ammo
    "ammo:physical": ("Ammo (physical)", "Ammo for ranged attacks and physical ranged weapon skills (Last Stand, etc.). You go back to this after using special ammo. Pick one (choosing again replaces it)." + AMMO_HELP_TAIL_EN),
    "ammo:magical": ("Ammo (magical)", "Ammo for magical ranged weapon skills (Leaden Salute, Wildfire, Trueflight, etc.). If not set, the physical ammo is used. Pick one." + AMMO_HELP_TAIL_EN),
    "ammo:quickdraw": ("Ammo (Quick Draw)", "Ammo for Quick Draw (Animikii Bullet, etc.). You go back to the physical ammo afterwards so you don't fire it with ranged attacks. Pick one." + AMMO_HELP_TAIL_EN),
    "ammo:special": ("Ammo (special, per weapon skill)", "Ammo used only for specific weapon skills (e.g. Hauksbok Bullet for Aeolian Edge or Savage Blade). Pick the ammo, then the weapon skills that use it. It's worn only for that weapon skill, then you go back to the physical ammo (so it isn't fired by accident). Choosing other ammo for the same weapon skill replaces it." + AMMO_HELP_TAIL_EN),
    # weapon skill variants
    "sets.precast.WS.Magic": ("Weapon skill (magical / hybrid)", "Gear worn for magical weapon skills (Sanguine Blade, Aeolian Edge, Leaden Salute, etc., hybrid ones included): Magic Attack, Magic Damage, weapon skill damage. The kit already knows which weapon skills are magical. Magical weapon skills you add per skill are built on top of this set (set_combine). On RNG/COR, if you make \"Weapon skill (ranged magical)\", ranged magical weapon skills use that instead."),
    "sets.precast.WS.Critical": ("Weapon skill (critical)", "Gear worn for weapon skills whose damage rides on critical hits (Evisceration, Vorpal Blade, Rampage, Blade: Jin, etc.): Critical hit rate, Critical hit damage, DEX. The kit already knows which weapon skills are critical ones. Critical weapon skills you add per skill are built on top of this set."),
    "sets.precast.WS.RangeMagic": ("Weapon skill (ranged magical)", "Gear worn for magical ranged weapon skills (Leaden Salute, Wildfire, Trueflight, etc.): Magic Attack, Magic Damage, Ranged Accuracy. If left empty, \"Weapon skill (magical / hybrid)\" is used. Ranged magical weapon skills you add per skill are built on top of this set."),
    "sets.precast.WS.Range": ("Weapon skill (ranged physical)", "Gear worn for physical Archery and Marksmanship weapon skills (Jishnu's Radiance, Last Stand, etc.): Ranged Attack, Ranged Accuracy, weapon skill damage. Magical ranged weapon skills such as Leaden Salute use \"Weapon skill (magical / hybrid)\"."),
    # ranged (RNG / COR)
    "sets.precast.RA": ("Ranged precast (Snapshot)", "Gear worn the moment you start a ranged attack: Snapshot, Rapid Shot and anything else that speeds up the draw."),
    "sets.RA_STP": ("Ranged attack (Store TP)", "Your base gear while a ranged attack is going off (sets.midcast.RA): Store TP, Ranged Attack, Ranged Accuracy."),
    "sets.RA_ACC": ("Ranged attack (accuracy)", "Ranged attack gear for when you need more Ranged Accuracy (//gs c cycle RangedMode to Acc; sets.midcast.RA.Acc)."),
    # COR
    "sets.CorsairRoll": ("Phantom Roll (default)", "Gear worn the moment you use Phantom Roll (sets.precast.CorsairRoll): roll area, roll duration, recast and so on. Per-roll gear (Chasseur's Tricorne +3 for Allies' Roll, etc.) is built on top of this set."),
    "sets.RA_QDSTP": ("Quick Draw (Store TP)", "Quick Draw gear that favors Store TP (e.g. for Sortie): Quick Draw damage, Store TP. If you also make \"Quick Draw (damage)\", //gs c cycle QuickDrawMode switches between them (StoreTP / Damage)."),
    "sets.RA_QDDPS": ("Quick Draw (damage)", "Quick Draw gear that goes for damage: Magic Attack, Quick Draw damage, AGI. Worn when QuickDrawMode is set to Damage."),
    "sets.RA_QDACC": ("Quick Draw (M.Acc: Light / Dark)", "Gear for Light Shot and Dark Shot, where landing the shot matters more than damage: Magic Accuracy. These two always use this set, whatever QuickDrawMode is set to."),
    # spell families
    "sets.midcast.Cure": ("Cure", "Gear worn while casting Cure I-VI: Cure potency, MND, Healing Magic skill. If left empty, \"Midcast (Healing Magic)\" is used."),
    "sets.precast.FC.Cure": ("Precast (Cure)", "Gear worn when you start casting a Cure: Cure spellcasting time - (Cure-only fast cast). If left empty, \"Precast (Fast Cast)\" is used."),
    "sets.midcast.Regen": ("Regen", "Gear worn while casting Regen I-V: Regen potency and duration."),
    "sets.midcast.Refresh": ("Refresh", "Gear worn while casting Refresh I-III: Refresh potency and duration."),
    "sets.midcast.Drain": ("Drain / Aspir", "Gear worn while casting Drain and Aspir: Drain/Aspir potency, Dark Magic skill, Magic Accuracy."),
    "sets.midcast.Helix": ("Helix", "Gear worn while casting helixes (Pyrohelix, etc.): Magic Attack, Magic Damage. Helixes sometimes want different gear from your nukes."),
    "sets.midcast.ElementalEnfeeble": ("Elemental debuffs (Burn, Shock...)", "Gear worn while casting Burn, Frost, Choke, Rasp, Shock or Drown: Magic Accuracy, INT."),
    # DNC
    "sets.precast.Waltz": ("Waltz", "Gear worn the moment you use a Waltz (Curing Waltz, etc.): Waltz potency, CHR, Waltz recast -."),
    "sets.precast.Samba": ("Samba", "Gear worn the moment you use a Samba: Samba duration +."),
    "sets.precast.Jig": ("Jig", "Gear worn the moment you use a Jig (Spectral Jig, etc.): Jig duration +."),
    "sets.precast.Step": ("Step", "Gear worn the moment you use a Step: Accuracy, so the step lands."),
    "sets.precast.Flourish1": ("Flourish I (Violent Flourish...)", "Gear worn the moment you use a Flourish I (Animated Flourish, Violent Flourish, etc.): Magic Accuracy, Accuracy."),
    # 1.1.0 additions
    "sets.TreasureHunter": ("Treasure Hunter (manual toggle)", "Treasure Hunter gear. Use //gs c toggle TreasureHunter in game to layer it over your engaged gear (not idle). Once the mob is tagged, toggle it off again."),
    "sets.engaged.dual11": ("Dual wield (/NIN)", "Layered over your engaged gear while you're /NIN: earrings, waist and so on that bring your Dual Wield to where you want it. Applied automatically based on your subjob."),
    "sets.engaged.dual21": ("Dual wield (/DNC)", "Layered over your engaged gear while you're /DNC. Applied automatically based on your subjob."),
    "sets.midcast['精霊魔法'].MB": ("Midcast (Elemental: magic burst)", "Elemental nuke gear for magic bursts: Magic Burst damage, Magic Attack. Built on top of \"Midcast (Elemental Magic)\". Worn when //gs c cycle CastingMode is set to MB."),
    "sets.idle.Refresh": ("Idle (Refresh)", "Idle gear for getting MP back (Refresh). Worn when //gs c cycle IdleMode is set to Refresh."),
    "sets.engaged.Acc": ("Engaged (accuracy)", "Engaged gear for when you're missing too much. Worn when //gs c cycle OffenseMode is set to Acc."),
    "sets.engaged.SubtleBlow": ("Engaged (Subtle Blow)", "Gear that gives the mob less TP (Subtle Blow). Worn when //gs c cycle OffenseMode is set to SubtleBlow."),
    "sets.precast.FC['歌唱']": ("Precast (songs)", "Gear worn when you start singing: song spellcasting time -, Fast Cast."),
    "sets.midcast.BluePhysical": ("Blue Magic (physical)", "Gear worn while casting physical blue spells (Sinker Drill, etc.): STR, DEX, Accuracy, Attack. The kit already knows which spells are physical."),
    "sets.midcast.BlueMagical": ("Blue Magic (magical)", "Gear worn while casting magical blue spells (Anvil Lightning, Tenebral Crush, etc.): Magic Attack, INT, Magic Accuracy."),
    "sets.midcast.BlueBuff": ("Blue Magic (buffs)", "Gear worn while casting buffing blue spells (Cocoon, Erratic Flutter, etc.): Blue Magic skill, duration."),
    "sets.midcast.BlueHealing": ("Blue Magic (healing)", "Gear worn while casting healing blue spells (Magic Fruit, White Wind, etc.): Cure potency, MND, VIT."),
    "sets.idle.Luopan": ("Idle (luopan out)", "Idle gear while you have a luopan out: luopan damage taken -, luopan Regen and the like. Without a luopan, the regular Idle set is used."),
    "sets.midcast.Entrust": ("Indi spell under Entrust", "Gear worn while you cast an Indi spell on someone else after Entrust: Indi duration + and the like."),
    "sets.midcast.March": ("Song (March)", "Gear worn while singing Marchs: March effect +, Singing skill."),
    "sets.midcast.Minuet": ("Song (Minuet)", "Gear worn while singing Minuets: Minuet effect +."),
    "sets.midcast.Madrigal": ("Song (Madrigal)", "Gear worn while singing Madrigals: Madrigal effect +."),
    "sets.midcast.Ballad": ("Song (Ballad)", "Gear worn while singing Ballads: Ballad effect +."),
    "sets.midcast.Minne": ("Song (Minne)", "Gear worn while singing Minnes: Minne effect +."),
    "sets.midcast.Paeon": ("Song (Paeon)", "Gear worn while singing Paeons: Paeon effect +."),
    "sets.midcast.Etude": ("Song (Etude)", "Gear worn while singing Etudes: Etude effect +."),
    "sets.midcast.Carol": ("Song (Carol)", "Gear worn while singing Carols: Carol effect +."),
    "sets.midcast.Prelude": ("Song (Prelude)", "Gear worn while singing Preludes: Prelude effect +."),
    "sets.midcast.Mambo": ("Song (Mambo)", "Gear worn while singing Mambos: Mambo effect +."),
    "sets.midcast.Lullaby": ("Song (Lullaby)", "Gear worn while singing Lullabies: Magic Accuracy, Singing skill, duration."),
    "sets.midcast.Threnody": ("Song (Threnody)", "Gear worn while singing Threnodies: Magic Accuracy, Threnody effect +."),
    "sets.midcast.Elegy": ("Song (Elegy)", "Gear worn while singing Elegies: Magic Accuracy, Singing skill."),
    "sets.midcast.Requiem": ("Song (Requiem)", "Gear worn while singing Requiems: Magic Accuracy, Singing skill."),
    "sets.midcast.BarElement": ("Midcast (Bar-element spells)", "Gear worn while casting elemental bar spells (Barfire, Barfira, etc.): bar-spell effect + (e.g. Shedir Seraweels). Built on top of \"Midcast (Enhancing Magic)\", so you only need the slots you want to change."),
}


def _attach_en():
    groups = [(None, COMMON), (None, WEAPON_ENTRIES), (None, AMMO_ENTRIES), (None, RANGED_ENTRIES),
              (None, list(SPELL_FAMILY_ENTRIES.values())),
              (None, [e for _j, e in EXTRA_ENTRIES]),
              (None, [WS_MAGIC_ENTRY, WS_CRIT_ENTRY, WS_RANGE_MAGIC_ENTRY, WS_RANGE_ENTRY, BAR_ELEMENT_ENTRY])]
    groups += list(JOB.items())
    for job, lst in groups:
        for e in lst:
            t = _EN.get("%s:%s" % (job, e["path"])) or _EN[e["path"]]
            e["title_en"], e["help_en"] = t


_attach_en()


def title(e):
    """場面の題名 (今の言語。英語が無ければ日本語)。"""
    return L(e["title"], e.get("title_en") or e["title"])


def help_text(e):
    """場面の説明 (今の言語。英語が無ければ日本語)。"""
    return L(e["help"], e.get("help_en") or e["help"])


# 技ごとの追加の種類 (CUSTOM_KINDS と同じ順) の英語
CUSTOM_KINDS_EN = [
    ("Weapon skill", "Enter a weapon skill name (e.g. Leaden Salute). This gear is worn only the moment you use it."),
    ("Job ability", "Enter an ability name (e.g. Manawell). This gear is worn only the moment you use it."),
    ("Spell", "Enter a spell name (e.g. Cure IV). This gear is worn only while you cast it."),
    ("Pet move", "Enter an avatar or pet move (e.g. Volt Strike). This gear is worn only while the move is performed."),
    ("Received buffs", "Gear that strengthens Phalanx, Protect and Shell cast on you by others (or yourself), such as Sheltered Ring. "
     "It's put on when the spell starts casting on you and taken off once it lands."),
]


def kind_label(i):
    """技ごとの追加の種類の名前 (今の言語)。app.py のドロップダウン用。"""
    return L(CUSTOM_KINDS[i][1], CUSTOM_KINDS_EN[i][0])


def kind_help(i):
    return L(CUSTOM_KINDS[i][2], CUSTOM_KINDS_EN[i][1])


RECEIVED_EN = {
    "IncreasedPhalanx": "Phalanx received + (boosts Phalanx cast on you)",
    "IncreasedProtect": "Protect received + (boosts Protect cast on you)",
    "IncreasedShell": "Shell received + (boosts Shell cast on you)",
}
RECEIVED_HELP_EN = ("Gear that strengthens spells cast on you by others (or yourself). It's put on when the spell starts casting on you, "
                    "and taken off once it lands (or after 8 seconds). For area spells (Protectra, Shellra, Phalanx after the "
                    "scholar's Accession), it's put on when a party member casts them. When you cast it on yourself, it's worn during the cast.")


def received_label(name):
    """被強化の装備の表示名 (name = IncreasedPhalanx など。今の言語)。"""
    for en, ja, _ids, _aoe in RECEIVED:
        if en == name:
            return L(ja, RECEIVED_EN.get(en, en))
    return name


def received_help():
    return L(RECEIVED_HELP, RECEIVED_HELP_EN)

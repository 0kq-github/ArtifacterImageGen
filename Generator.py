from io import BytesIO
from PIL import Image,ImageFont,ImageDraw,ImageEnhance
import json
import os 
import requests
from typing import List
from enkanetwork import EnkaNetworkAPI, CharacterInfo, CharacterSkill, Equipments, EquipmentsStats
from collections import Counter
import base64

from PIL import ImageFile


class CynoGenerator:
    def __init__(self,cwd = "./ArtifacterImageGen"):
        ImageFile.LOAD_TRUNCATED_IMAGES = True
        self.cwd = cwd
        self.status_prop = self.read_json(self.cwd+"/mapping/status_prop.json")
        self.subop = self.set_subop()
        self.score_type_dict = {
            "ATTACK":"攻撃力",
            "HP":"HP",
            "DEFENSE":"防御力",
            "EFFICIENCY":"元素チャージ効率",
            "ELEMENT":"元素熟知",
        }
        self.elements = {
            "Pyro":"炎元素ダメージ",
            "Electro":"雷元素ダメージ",
            "Hydro":"水元素ダメージ",
            "Dendro":"草元素ダメージ",
            "Anemo":"風元素ダメージ",
            "Geo":"岩元素ダメージ",
            "Cryo":"氷元素ダメージ"
        }
        os.makedirs(self.cwd+"/cache",exist_ok=True)
        self.client = EnkaNetworkAPI(lang="jp")

    def read_json(self,path):
        with open(path,encoding='utf-8') as f:
            data = json.load(f)
        return data

    def write_json(self,data,path):
        with open(path,mode="w",encoding='utf-8') as f:
            json.dump(data,f)

    def set_subop(self):
        if not os.path.exists(self.cwd+"mapping/subop.json"):
            resp = requests.get("https://raw.githubusercontent.com/Sycamore0/GenshinData/main/ExcelBinOutput/ReliquaryAffixExcelConfigData.json")
            sub_stats_data = resp.json()

            result = {}
            for i in sub_stats_data:
                if not i["propType"] in result.keys():
                    result[i["propType"]] = {}
                key_1 = i["propType"]
                key_2 = i["id"]
                del i["id"]
                del i["propType"]
                result[key_1][key_2] = i

            self.write_json(result,self.cwd+"/mapping/subop.json")
        result = self.read_json(self.cwd+"/mapping/subop.json")
        return result

    def set_artifact(self,artifact:Equipments,score_type:str):
        score = 0.0
        result = {
            "type":artifact.detail.artifact_name_set,
            "Level":artifact.level,
            "rarelity":artifact.detail.rarity,
            "filename":self.get_image(artifact.detail.icon.filename,artifact.detail.icon.url),
            "main": {
                "option": self.status_prop[artifact.detail.mainstats.prop_id],
            },
            "sub": []
        }
        if artifact.detail.mainstats.prop_id in ["FIGHT_PROP_ELEMENT_MASTERY","FIGHT_PROP_HP","FIGHT_PROP_ATTACK","FIGHT_PROP_DEFENSE"]:
            result["main"]["value"] = int(artifact.detail.mainstats.value)
        else:
            result["main"]["value"] = artifact.detail.mainstats.value
        for sub_stat in artifact.detail.substats:
            stat = {
                "option": self.status_prop[sub_stat.prop_id],
            }
            if sub_stat.prop_id in ["FIGHT_PROP_ELEMENT_MASTERY","FIGHT_PROP_HP","FIGHT_PROP_ATTACK","FIGHT_PROP_DEFENSE"]:
                stat["value"] = round(sub_stat.value)
            else:
                stat["value"] = sub_stat.value
            match sub_stat.prop_id:
                case "FIGHT_PROP_CRITICAL":
                    score += (sub_stat.value * 2)
                case "FIGHT_PROP_CRITICAL_HURT":
                    score += sub_stat.value
            match score_type:
                case "HP":
                    if sub_stat.prop_id == "FIGHT_PROP_HP_PERCENT":
                        score += sub_stat.value
                case "ATTACK":
                    if sub_stat.prop_id == "FIGHT_PROP_ATTACK_PERCENT":
                        score += sub_stat.value
                case "DEFENSE":
                    if sub_stat.prop_id == "FIGHT_PROP_DEFENSE_PERCENT":
                        score += sub_stat.value
                case "EFFICIENCY":
                    if sub_stat.prop_id == "FIGHT_PROP_CHARGE_EFFICIENCY":
                        score += sub_stat.value
                case "ELEMENT":
                    if sub_stat.prop_id == "FIGHT_PROP_ELEMENT_MASTERY":
                        score += (sub_stat.value * 0.25)
            if not "values" in stat.keys():
                stat["values"] = []
            for i in artifact.props:
                if str(i.id) in self.subop[sub_stat.prop_id].keys():
                    if sub_stat.prop_id in ["FIGHT_PROP_ELEMENT_MASTERY","FIGHT_PROP_HP","FIGHT_PROP_ATTACK","FIGHT_PROP_DEFENSE"]:
                        stat["values"].append(round(self.subop[sub_stat.prop_id][str(i.id)]["propValue"]))
                    else:
                        stat["values"].append(round(self.subop[sub_stat.prop_id][str(i.id)]["propValue"]*100,1))
            stat["values"].sort()
            
            result["sub"].append(stat)
        return result, round(score,1)

    def set_buff(self,c:CharacterInfo):
        result = {}
        stats = c.stats
        if stats.FIGHT_PROP_PHYSICAL_ADD_HURT.value > 0:
            result["物理ダメージ"] = round(stats.FIGHT_PROP_PHYSICAL_ADD_HURT.value * 100,1)
        if stats.FIGHT_PROP_FIRE_ADD_HURT.value > 0:
            result["炎元素ダメージ"] = round(stats.FIGHT_PROP_FIRE_ADD_HURT.value * 100,1)
        if stats.FIGHT_PROP_ELEC_ADD_HURT.value > 0:
            result["雷元素ダメージ"] = round(stats.FIGHT_PROP_ELEC_ADD_HURT.value * 100,1)
        if stats.FIGHT_PROP_WATER_ADD_HURT.value > 0:
            result["水元素ダメージ"] = round(stats.FIGHT_PROP_WATER_ADD_HURT.value * 100,1)
        if stats.FIGHT_PROP_GRASS_ADD_HURT.value > 0:
            result["草元素ダメージ"] = round(stats.FIGHT_PROP_GRASS_ADD_HURT.value * 100,1)
        if stats.FIGHT_PROP_WIND_ADD_HURT.value > 0:
            result["風元素ダメージ"] = round(stats.FIGHT_PROP_WIND_ADD_HURT.value * 100,1)
        if stats.FIGHT_PROP_ROCK_ADD_HURT.value > 0:
            result["岩元素ダメージ"] = round(stats.FIGHT_PROP_ROCK_ADD_HURT.value * 100,1)
        if stats.FIGHT_PROP_ICE_ADD_HURT.value > 0:
            result["氷元素ダメージ"] = round(stats.FIGHT_PROP_ICE_ADD_HURT.value * 100,1)
        if stats.FIGHT_PROP_HEAL_ADD.value > 0:
            result["与える治癒効果"] = round(stats.FIGHT_PROP_HEAL_ADD.value * 100,1)

        element = self.elements[c.element.name]
        if result.values():
            max_value =  max(result.values())
            for k,v in sorted(result.items()):
                if v == max_value:
                    if k == element:
                        return k,v
        else:
            return None,None
        max_value = max(result.values())
        for k,v in result.items():
            if v == max_value:
                return k,v

    def get_image(self,filename:str,url):
        if os.path.exists(self.cwd+"/cache/"+filename+".png"):
            return self.cwd+"/cache/"+filename+".png"
        else:
            resp = requests.get(url)
            with open(self.cwd+"/cache/"+filename+".png",mode="wb") as f:
                f.write(resp.content)
            return self.cwd+"/cache/"+filename+".png"

    def resize_image(self,filename):
        # 画像を読み込む
        image = Image.open(filename)

        # 縦横比を保ったまま、縦の長さが1200ピクセルになるようにリサイズする
        width, height = image.size
        new_height = 1200
        new_width = int(width * new_height / height)
        resized_image = image.resize((new_width, new_height))

        # 透明な背景の新しい画像を作成する
        background = Image.new('RGBA', (2048, 1200), (0, 0, 0, 0))

        # リサイズした画像を中央に配置する
        x = int((2048 - new_width) / 2)
        y = int((1200 - new_height) / 2)
        background.paste(resized_image, (x, y))

        # 画像を保存する
        background.save(filename,"png")

    def generation(self,character:CharacterInfo,score_type:str,background_path:str):
        #config 
        element = character.element.name
        
        #CharacterData :dict = data.get('Character')
        CharacterName : str = character.name
        CharacterConstellations :int = character.constellations_unlocked
        CharacterLevel : int = character.level
        if (character.id == 10000005) or (character.id == 10000007):
            FriendShip = None
        else:
            FriendShip : int = character.friendship_level
        #CharacterStatus : CharacterStats = character.stats
        CharacterStatus : dict = {
            "HP": round(character.stats.FIGHT_PROP_MAX_HP.value),
            "攻撃力": round(character.stats.FIGHT_PROP_CUR_ATTACK.value),
            "防御力": round(character.stats.FIGHT_PROP_CUR_DEFENSE.value),
            "元素熟知": round(character.stats.FIGHT_PROP_ELEMENT_MASTERY.value),
            "会心率": round(character.stats.FIGHT_PROP_CRITICAL.value*100,1),
            "会心ダメージ": round(character.stats.FIGHT_PROP_CRITICAL_HURT.value*100,1),
            "元素チャージ効率": round(character.stats.FIGHT_PROP_CHARGE_EFFICIENCY.value*100,1)
            }
        buff,value = self.set_buff(character)
        if buff:
            CharacterStatus[buff] = value
        CharacterBase : dict = {
            "HP":round(character.stats.BASE_HP.value),
            "攻撃力":round(character.stats.FIGHT_PROP_BASE_ATTACK.value),
            "防御力":round(character.stats.FIGHT_PROP_BASE_DEFENSE.value)
            }
        CharacterTalent: List[CharacterSkill] = character.skills
        
        Weapon : Equipments = character.equipments[-1]
        WeaponName : str = Weapon.detail.name
        WeaponLevel : int = Weapon.level
        WeaponRank : int = Weapon.refinement
        WeaponRarity : int = Weapon.detail.rarity
        WeaponBaseATK: int = round(Weapon.detail.mainstats.value)
        WeaponSubOP : EquipmentsStats = Weapon.detail.substats[0] if Weapon.detail.substats else None
        WeaponSubOPKey : str = WeaponSubOP.name if WeaponSubOP else None
        WeaponSubOPValue : int | float = WeaponSubOP.value if WeaponSubOP else None
        
        ScoreData : dict = {}
        ScoreCVBasis : str = score_type
        ArtifactsData: dict = {}
        ScoreTotal = 0.0
        for e in character.equipments:
            match e.detail.artifact_type.value:
                case "EQUIP_BRACER":
                    ArtifactsData["flower"],score = self.set_artifact(e,score_type)
                    ScoreData["flower"] = score
                    ScoreTotal += score
                case "EQUIP_NECKLACE":
                    ArtifactsData["wing"],score = self.set_artifact(e,score_type)
                    ScoreData["wing"] = score
                    ScoreTotal += score
                case "EQUIP_SHOES":
                    ArtifactsData["clock"],score = self.set_artifact(e,score_type)
                    ScoreData["clock"] : float = score
                    ScoreTotal += score
                case "EQUIP_RING":
                    ArtifactsData["cup"],score = self.set_artifact(e,score_type)
                    ScoreData["cup"] = score
                    ScoreTotal += score
                case "EQUIP_DRESS":
                    ArtifactsData["crown"],score = self.set_artifact(e,score_type)
                    ScoreData["crown"] = score
                    ScoreTotal += score
        ScoreTotal = round(ScoreTotal,1)
        
        config_font = lambda size : ImageFont.truetype(f'{self.cwd}/Assets/ja-jp.ttf',size)
        
        if background_path:
            if background_path.startswith("http") or background_path.startswith("https"):
                background = BytesIO(requests.get(background_path).content)
            else:
                background = background_path
            Base = Image.open(background).resize((1920,1080)).convert("RGBA")
        else:
            Base = Image.open(f'{self.cwd}/Base/{element}.png')
        
        if (character.id == 10000005) or (character.id == 10000007):
            if not os.path.exists(self.cwd+"/cache/"+character.image.banner.filename+".png"):
                self.resize_image(self.get_image(character.image.banner.filename,character.image.banner.url))
        CharacterImage = Image.open(self.get_image(character.image.banner.filename,character.image.banner.url)).convert("RGBA")                
        
        CharacterBack = Image.new('RGBA', (2048, 1024), (0, 0, 0, 0))
        x = int((2048 - CharacterImage.width) / 2)
        y = int((1024 - CharacterImage.height) / 2)
        CharacterBack.paste(CharacterImage, (x, y))
        CharacterImage = CharacterBack
        Shadow = Image.open(f'{self.cwd}/Assets/Shadow.png').resize(Base.size)
        CharacterImage = CharacterImage.crop((289,0,1728,1024))
        CharacterImage = CharacterImage.resize((int(CharacterImage.width*0.75), int(CharacterImage.height*0.75)))
        
        CharacterAvatarMask = CharacterImage.copy()
        
        if CharacterName in ['アルハイゼン','ヌヴィレット']:
            CharacterAvatarMask2 = Image.open(f'{self.cwd}/Assets/Alhaitham.png').convert('L').resize(CharacterImage.size)
        else:
            CharacterAvatarMask2 = Image.open(f'{self.cwd}/Assets/CharacterMask.png').convert('L').resize(CharacterImage.size)
        CharacterImage.putalpha(CharacterAvatarMask2)
        
        CharacterPaste = Image.new("RGBA",Base.size,(255,255,255,0))
        
        CharacterPaste.paste(CharacterImage,(-160,-45),mask=CharacterAvatarMask)
        Base = Image.alpha_composite(Base,CharacterPaste)
        Base = Image.alpha_composite(Base,Shadow)
        
        
        #武器
        WeaponBase = Image.open(self.get_image(Weapon.detail.icon.filename,Weapon.detail.icon.url)).convert("RGBA").resize((128,128))
        WeaponPaste = Image.new("RGBA",Base.size,(255,255,255,0))
        
        WeaponMask = WeaponBase.copy()
        WeaponPaste.paste(WeaponBase,(1430,50),mask=WeaponMask)
        
        Base = Image.alpha_composite(Base,WeaponPaste)
        
        WeaponRImage = Image.open(f'{self.cwd}/Assets/Rarelity/{WeaponRarity}.png').convert("RGBA")
        WeaponRImage = WeaponRImage.resize((int(WeaponRImage.width*0.97),int(WeaponRImage.height*0.97)))
        WeaponRPaste = Image.new("RGBA",Base.size,(255,255,255,0))
        WeaponRMask = WeaponRImage.copy()
        
        WeaponRPaste.paste(WeaponRImage,(1422,173),mask=WeaponRMask)
        Base = Image.alpha_composite(Base,WeaponRPaste)
        
        #天賦
        TalentBase = Image.open(f'{self.cwd}/Assets/TalentBack.png')
        TalentBasePaste = Image.new("RGBA",Base.size,(255,255,255,0))
        TalentBase = TalentBase.resize((int(TalentBase.width/1.5),int(TalentBase.height/1.5)))
        
        for i in range(3):
            TalentPaste = Image.new("RGBA",TalentBase.size,(255,255,255,0))
            Talent = Image.open(self.get_image(character.skills[i].icon.filename,character.skills[i].icon.url)).resize((50,50)).convert('RGBA')
            TalentMask = Talent.copy()
            TalentPaste.paste(Talent,(TalentPaste.width//2-25,TalentPaste.height//2-25),mask=TalentMask)
            
            TalentObject = Image.alpha_composite(TalentBase,TalentPaste)
            TalentBasePaste.paste(TalentObject,(15,330+i*105))
            
        Base = Image.alpha_composite(Base,TalentBasePaste)
        
        #凸
        CBase = Image.open(f'{self.cwd}/命の星座/{element}.png').resize((90,90)).convert('RGBA')
        Clock = Image.open(f'{self.cwd}/命の星座/{element}LOCK.png').resize((90,90)).convert('RGBA')
        ClockMask = Clock.copy()
        
        CPaste = Image.new("RGBA",Base.size,(255,255,255,0))
        for c in range(1,7):
            if c > CharacterConstellations:
                CPaste.paste(Clock,(666,-10+c*93),mask=ClockMask)
            else:
                CharaC = Image.open(self.get_image(character.constellations[c-1].icon.filename,character.constellations[c-1].icon.url)).convert("RGBA").resize((45,45))
                CharaCPaste = Image.new("RGBA",CBase.size,(255,255,255,0))
                CharaCMask = CharaC.copy()
                CharaCPaste.paste(CharaC,(int(CharaCPaste.width/2)-25,int(CharaCPaste.height/2)-23),mask=CharaCMask)
                
                Cobject = Image.alpha_composite(CBase,CharaCPaste)
                CPaste.paste(Cobject,(666,-10+c*93))
        
        Base = Image.alpha_composite(Base,CPaste)
        D = ImageDraw.Draw(Base)
        
        D.text((30,20),CharacterName,font=config_font(48))
        levellength = D.textlength("Lv."+str(CharacterLevel),font=config_font(25))
        D.text((35,75),"Lv."+str(CharacterLevel),font=config_font(25))
        if FriendShip:
            friendshiplength = D.textlength(str(FriendShip),font=config_font(25))
            D.rounded_rectangle((35+levellength+5,74,77+levellength+friendshiplength,102),radius=2,fill="black")
            FriendShipIcon = Image.open(f'{self.cwd}/Assets/Love.png').convert("RGBA")
            FriendShipIcon = FriendShipIcon.resize((int(FriendShipIcon.width*(24/FriendShipIcon.height)),24))
            Fmask = FriendShipIcon.copy()
            Base.paste(FriendShipIcon,(42+int(levellength),76),mask=Fmask)
            D.text((73+levellength,74),str(FriendShip),font=config_font(25))
        
        D.text((42,397),f'Lv.{CharacterTalent[0].level}',font=config_font(17),fill='aqua' if CharacterTalent[0].level >= 10 else None)
        D.text((42,502),f'Lv.{CharacterTalent[1].level}',font=config_font(17),fill='aqua' if CharacterTalent[1].level >= 10 else None)
        D.text((42,607),f'Lv.{CharacterTalent[2].level}',font=config_font(17),fill='aqua' if CharacterTalent[2].level >= 10 else None)
        
        def genbasetext(state):
            sumv = CharacterStatus[state]
            plusv = sumv - CharacterBase[state]
            basev = CharacterBase[state]
            return f"+{format(plusv,',')}",f"{format(basev,',')}",D.textlength(f"+{format(plusv,',')}",font=config_font(12)),D.textlength(f"{format(basev,',')}",font=config_font(12))
        
        disper = ['会心率','会心ダメージ','攻撃パーセンテージ','防御パーセンテージ','HPパーセンテージ','水元素ダメージ','物理ダメージ','風元素ダメージ','岩元素ダメージ','炎元素ダメージ','与える治癒効果','与える治療効果','雷元素ダメージ','氷元素ダメージ','草元素ダメージ','与える治癒効果','元素チャージ効率']
        StateOP = ('HP','攻撃力',"防御力","元素熟知","会心率","会心ダメージ","元素チャージ効率")
        for k,v in CharacterStatus.items():
            if k in ['氷元素ダメージ','水元素ダメージ','岩元素ダメージ','草元素ダメージ','風元素ダメージ','炎元素ダメージ','物理ダメージ','与える治癒効果','雷元素ダメージ'] and v == 0:
                k = f'{element}元素ダメージ'
            try:
                i = StateOP.index(k)
            except:
                i = 7
                D.text((844,67+i*70),k,font=config_font(26))
                opicon = Image.open(f'{self.cwd}/emotes/{k}.png').resize((40,40))
                oppaste = Image.new('RGBA',Base.size,(255,255,255,0))
                opmask = opicon.copy()
                oppaste.paste(opicon,(789,65+i*70))
                Base = Image.alpha_composite(Base,oppaste)
                D = ImageDraw.Draw(Base)
            
            if k not in disper:
                statelen = D.textlength(format(v,","),config_font(26))
                D.text((1360-statelen,67+i*70),format(v,","),font=config_font(26))
            else:
                statelen = D.textlength(f'{float(v)}%',config_font(26))
                D.text((1360-statelen,67+i*70),f'{float(v)}%',font=config_font(26))
                
            if k in ['HP','防御力','攻撃力']:
                HPpls,HPbase,HPsize,HPbsize = genbasetext(k)
                D.text((1360-HPsize,97+i*70),HPpls,fill=(0,255,0,180),font=config_font(12))
                D.text((1360-HPsize-HPbsize-1,97+i*70),HPbase,font=config_font(12),fill=(255,255,255,180))
        
            
        D.text((1582,47),WeaponName,font=config_font(26))
        wlebellen = D.textlength(f'Lv.{WeaponLevel}',font=config_font(24))
        D.rounded_rectangle((1582,80,1582+wlebellen+4,108),radius=1,fill='black')
        D.text((1584,82),f'Lv.{WeaponLevel}',font=config_font(24))
        

        BaseAtk = Image.open(f'{self.cwd}/emotes/基礎攻撃力.png').resize((23,23))
        BaseAtkmask = BaseAtk.copy().convert("RGBA")
        Base.paste(BaseAtk,(1600,120),mask=BaseAtkmask)
        D.text((1623,120),f'基礎攻撃力  {WeaponBaseATK}',font=config_font(23))
        
        optionmap = {
            "攻撃パーセンテージ":"攻撃%",
            "防御パーセンテージ":"防御%",
            "元素チャージ効率":"元チャ効率",
            "HPパーセンテージ":"HP%",
        }
        if WeaponSubOPKey != None:
            BaseAtk = Image.open(f'{self.cwd}/emotes/{WeaponSubOPKey}.png').resize((23,23))
            BaseAtkmask = BaseAtk.copy().convert("RGBA")
            Base.paste(BaseAtk,(1600,155),mask=BaseAtkmask)
            
            D.text((1623,155),f'{optionmap.get(WeaponSubOPKey) or WeaponSubOPKey}  {str(WeaponSubOPValue)+"%" if isinstance(WeaponSubOPValue,float) else format(WeaponSubOPValue,",")}',font=config_font(23))
        
            
        
        D.rounded_rectangle((1430,45,1470,70),radius=1,fill='black')
        D.text((1433,46),f'R{WeaponRank}',font=config_font(24))
        
        ScoreLen = D.textlength(f'{ScoreTotal}',config_font(75))
        D.text((1652-ScoreLen//2,420),str(ScoreTotal),font=config_font(75))
        blen = D.textlength(f'{self.score_type_dict[ScoreCVBasis]}換算',font=config_font(24))
        D.text((1867-blen,585),f'{self.score_type_dict[ScoreCVBasis]}換算',font=config_font(24))
        
        if ScoreTotal >= 220:
            ScoreEv =Image.open(f'{self.cwd}/artifactGrades/SS.png')
        elif ScoreTotal >= 200:
            ScoreEv =Image.open(f'{self.cwd}/artifactGrades/S.png')
        elif ScoreTotal >= 180:
            ScoreEv =Image.open(f'{self.cwd}/artifactGrades/A.png')
        else:
            ScoreEv =Image.open(f'{self.cwd}/artifactGrades/B.png')
        
        ScoreEv = ScoreEv.resize((ScoreEv.width//8,ScoreEv.height//8))
        EvMask = ScoreEv.copy()
        
        Base.paste(ScoreEv,(1806,345),mask=EvMask)
        
        #聖遺物
        atftype = list()
        for i,parts in enumerate(['flower',"wing","clock","cup","crown"]):
            details = ArtifactsData.get(parts)
            
            if not details:
                continue
            atftype.append(details['type'])
            PreviewPaste = Image.new('RGBA',Base.size,(255,255,255,0))
            Preview = Image.open(details["filename"]).convert("RGBA").resize((256,256))
            enhancer = ImageEnhance.Brightness(Preview)
            Preview = enhancer.enhance(0.6)
            Preview= Preview.resize((int(Preview.width*1.3),int(Preview.height*1.3)))
            Pmask1 = Preview.copy()
            
            Pmask = Image.open(f'{self.cwd}/Assets/ArtifactMask.png').convert('L').resize(Preview.size)
            Preview.putalpha(Pmask)
            if parts in ['flower','crown']:
                PreviewPaste.paste(Preview,(-37+373*i,570),mask=Pmask1)
            elif parts in ['wing','cup']:
                PreviewPaste.paste(Preview,(-36+373*i,570),mask=Pmask1)
            else:
                PreviewPaste.paste(Preview,(-35+373*i,570),mask=Pmask1)
            Base = Image.alpha_composite(Base,PreviewPaste)
            D = ImageDraw.Draw(Base)
            
            mainop = details['main']['option']
            
            mainoplen = D.textlength(optionmap.get(mainop) or mainop,font=config_font(29))
            D.text((375+i*373-int(mainoplen),655),optionmap.get(mainop) or mainop,font=config_font(29))
            MainIcon = Image.open(f'{self.cwd}/emotes/{mainop}.png').convert("RGBA").resize((35,35))
            MainMask = MainIcon.copy()
            Base.paste(MainIcon,(340+i*373-int(mainoplen),655),mask=MainMask)
            
            mainv = details['main']['value']
            if mainop in disper:
                mainvsize = D.textlength(f'{float(mainv)}%',config_font(49))
                D.text((375+i*373-mainvsize,690),f'{float(mainv)}%',font=config_font(49))
            else:
                mainvsize = D.textlength(format(mainv,","),config_font(49))
                D.text((375+i*373-mainvsize,690),format(mainv,","),font=config_font(49))
            levlen = D.textlength(f'+{details["Level"]}',config_font(21))
            D.rounded_rectangle((373+i*373-int(levlen),748,375+i*373,771),fill='black',radius=2)
            D.text((374+i*373-levlen,749),f'+{details["Level"]}',font=config_font(21))
                
            if len(details['sub']) == 0:
                continue
            
            for a,sub in enumerate(details['sub']):
                SubOP = sub['option']
                SubVal = sub['value']
                SubVals = sub["values"]
                if SubOP in ['HP','攻撃力','防御力']:
                    D.text((79+373*i,811+50*a),optionmap.get(SubOP) or SubOP,font=config_font(25),fill=(255,255,255,190))
                else:
                    D.text((79+373*i,811+50*a),optionmap.get(SubOP) or SubOP,font=config_font(25))
                SubIcon = Image.open(f'{self.cwd}/emotes/{SubOP}.png').resize((30,30))
                SubMask = SubIcon.copy().convert("RGBA")
                Base.paste(SubIcon,(44+373*i,811+50*a),mask=SubMask)
                if SubOP in disper:
                    SubSize = D.textlength(f'{float(SubVal)}%',config_font(25))
                    D.text((375+i*373-SubSize,811+50*a),f'{float(SubVal)}%',font=config_font(25))
                else:
                    SubSize = D.textlength(format(SubVal,","),config_font(25))
                    if SubOP in ['防御力','攻撃力','HP']:
                        D.text((375+i*373-SubSize,811+50*a),format(SubVal,","),font=config_font(25),fill=(255,255,255,190))
                    else:
                        D.text((375+i*373-SubSize,811+50*a),format(SubVal,","),font=config_font(25),fill=(255,255,255))
                
                if details['Level'] == 20 and details['rarelity'] == 5:
                    nobi = D.textlength("+".join(map(str,SubVals)),font=config_font(11))
                    D.text((375+i*373-nobi,840+50*a),"+".join(map(str,SubVals)),fill=(255, 255, 255, 160),font=config_font(11))
            
            Score = float(ScoreData[parts])
            ATFScorelen = D.textlength(str(Score),config_font(36))
            D.text((380+i*373-ATFScorelen,1016),str(Score),font=config_font(36))
            D.text((295+i*373-ATFScorelen,1025),'Score',font=config_font(27),fill=(160,160,160))
            
            PointRefer = {
                "total": {
                    "SS": 220,
                    "S": 200,
                    "A": 180
                },
                "flower": {
                    "SS": 50,
                    "S": 45,
                    "A": 40
                },
                "wing": {
                    "SS": 50,
                    "S": 45,
                    "A": 40
                },
                "clock": {
                    "SS": 45,
                    "S": 40,
                    "A": 35
                },
                "cup": {
                    "SS": 45,
                    "S": 40,
                    "A": 37
                },
                "crown": {
                    "SS": 40,
                    "S": 35,
                    "A": 30
                }
            }
            
            if Score >= PointRefer[parts]['SS']:
                ScoreImage =Image.open(f'{self.cwd}/artifactGrades/SS.png')
            elif Score >= PointRefer[parts]['S']:
                ScoreImage =Image.open(f'{self.cwd}/artifactGrades/S.png')
            elif Score >= PointRefer[parts]['A']:
                ScoreImage =Image.open(f'{self.cwd}/artifactGrades/A.png')
            else:
                ScoreImage =Image.open(f'{self.cwd}/artifactGrades/B.png')
                
            ScoreImage = ScoreImage.resize((ScoreImage.width//11,ScoreImage.height//11))
            SCMask = ScoreImage.copy()
            
            Base.paste(ScoreImage,(85+373*i,1013),mask=SCMask)
            
        SetBounus = Counter([x for x in atftype if atftype.count(x) >= 2])
        for i,(n,q) in enumerate(SetBounus.items()):
            if len(SetBounus) == 2:
                D.text((1536,243+i*35),n,fill=(0,255,0),font=config_font(23))
                D.rounded_rectangle((1818,243+i*35,1862,266+i*35),1,'black')
                D.text((1835,243+i*35),str(q),font=config_font(19))
            if len(SetBounus) == 1:
                D.text((1536,263),n,fill=(0,255,0),font=config_font(23))
                D.rounded_rectangle((1818,263,1862,288),1,'black')
                D.text((1831,265),str(q),font=config_font(19))
            
        buffer = BytesIO()
        Base.save(buffer,"png")
        return buffer
        #return pil_to_base64(Base,format='png')
        
    
    
def pil_to_base64(img, format="jpeg"):
    buffer = BytesIO()
    img.save(buffer, format)
    img_str = base64.b64encode(buffer.getvalue()).decode("ascii")

    return img_str
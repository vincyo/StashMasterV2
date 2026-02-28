#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
StashMaster V2 - Interface Unifiée
Fusion des Phase 1 et Phase 2 avec génération automatique de bio
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, simpledialog
import requests
from bs4 import BeautifulSoup
import re
import json
from datetime import datetime
from typing import Dict, List, Optional
import threading


class TagRulesEngine:
    """Moteur de règles pour générer des tags basés sur les métadonnées"""
    
    @staticmethod
    def generate_tags(metadata: Dict) -> List[str]:
        """Génère des tags basés sur les métadonnées collectées"""
        tags = []
        
        # Tags basés sur l'ethnicité
        ethnicity = metadata.get('ethnicity', '').lower()
        if ethnicity:
            if 'caucasian' in ethnicity:
                tags.append('Caucasian')
            elif 'latin' in ethnicity or 'cuban' in ethnicity:
                tags.append('Latina')
            elif 'asian' in ethnicity:
                tags.append('Asian')
            elif 'ebony' in ethnicity or 'african' in ethnicity:
                tags.append('Ebony')
        
        # Tags basés sur la couleur de cheveux
        hair_color = metadata.get('hair_color', '').lower()
        if 'blonde' in hair_color or 'blond' in hair_color:
            tags.append('Blonde')
        elif 'brown' in hair_color or 'brunette' in hair_color:
            tags.append('Brunette')
        elif 'red' in hair_color:
            tags.append('Redhead')
        elif 'black' in hair_color:
            tags.append('Black Hair')
        
        # Tags basés sur les mesures
        measurements = metadata.get('measurements', '')
        if measurements:
            # Extraire la taille des seins (première valeur)
            match = re.match(r'(\d+)', measurements)
            if match:
                size = int(match.group(1))
                if size >= 36:
                    tags.append('Big Boobs')
                elif size <= 32:
                    tags.append('Small Boobs')
        
        # Tags basés sur les piercings
        piercings = metadata.get('piercings', '').lower()
        if piercings and piercings != 'none':
            tags.append('Pierced')
        
        # Tags basés sur les tattoos
        tattoos = metadata.get('tattoos', '').lower()
        if tattoos and tattoos != 'none':
            tags.append('Tattooed')
        
        # Tags basés sur l'âge de carrière
        career_start = metadata.get('career_start', '')
        if career_start:
            try:
                year = int(career_start.split('-')[0])
                current_year = datetime.now().year
                if current_year - year > 10:
                    tags.append('MILF')
            except:
                pass
        
        return list(set(tags))  # Éliminer les doublons


class AwardsCleaner:
    """Nettoie et formate les awards pour avoir 1 par ligne"""
    
    @staticmethod
    def clean_awards(raw_awards: str) -> str:
        """Nettoie le texte brut des awards pour avoir un format lisible"""
        if not raw_awards:
            return ""
        
        # Séparer par les numéros d'année
        lines = []
        current_year = None
        
        # Pattern pour détecter les années
        year_pattern = re.compile(r'\b(19\d{2}|20\d{2})\b')
        
        # Pattern pour détecter les types d'awards
        award_types = ['AVN AWARDS', 'XBIZ AWARDS', 'NIGHTMOVES', 'XRCO AWARDS']
        
        text = raw_awards
        for award_type in award_types:
            text = text.replace(award_type, f'\n{award_type}\n')
        
        # Diviser en lignes et nettoyer
        for line in text.split('\n'):
            line = line.strip()
            if not line:
                continue
            
            # Détecter si c'est une année
            if re.match(r'^\d{4}$', line):
                current_year = line
                lines.append(f'\n{current_year}')
                continue
            
            # Détecter si c'est un type d'award
            if any(award_type in line.upper() for award_type in award_types):
                lines.append(f'\n{line}')
                continue
            
            # Détecter Winner ou Nominee
            if line.startswith('Winner:') or line.startswith('Nominee:'):
                lines.append(f'  {line}')
            elif current_year and not line.startswith(' '):
                lines.append(f'  {line}')
            else:
                lines.append(line)
        
        return '\n'.join(lines)


class BioGenerator:
    """Générateur de biographies avec Google Search et Ollama"""
    
    def __init__(self):
        self.ollama_url = "http://localhost:11434/api/generate"
    
    def generate_google_bio(self, performer_name: str, metadata: Dict) -> str:
        """Génère une bio de 3000 caractères style Google"""
        
        # Template basé sur BioGooglemodele.txt
        template = f"""### {performer_name} : L'étoile charismatique au parcours diversifié

**Introduction**
Née le {metadata.get('birthdate', '[date]')} à {metadata.get('birthplace', '[lieu]')}, {performer_name} a marqué de son empreinte l'industrie du divertissement pour adultes dès son entrée en scène en {metadata.get('career_start', '[année]')}. Reconnue pour son charisme naturel et son énergie captivante, elle a rapidement acquis une notoriété significative. Au fil de sa carrière, elle a adopté plusieurs pseudonymes, tels que {', '.join(metadata.get('aliases', []))}, qui ont tous contribué à forger son image polyvalente et à laisser un impact mémorable dans le secteur.

**📅 Origines et Premiers Pas**
Issue d'une famille d'origine {metadata.get('ethnicity', '[origine]')} et ayant grandi dans le vibrant paysage de {metadata.get('birthplace', '[lieu]')}, la vie de {performer_name} avant son immersion dans l'industrie est enveloppée d'une certaine discrétion. Les informations détaillées concernant son enfance ou son parcours scolaire ne sont pas largement divulguées publiquement, soulignant une volonté de préserver sa sphère privée. C'est à l'âge de {metadata.get('career_start_age', '[âge]')} ans, en {metadata.get('career_start', '[année]')}, qu'elle a franchi le seuil du monde du divertissement pour adultes, un choix qui allait définir une décennie de sa vie professionnelle et la propulser sur le devant de la scène internationale.

**🏆 Carrière et Filmographie**
La trajectoire professionnelle de {performer_name} a débuté avec une force considérable, la menant à collaborer avec certains des plus grands noms de l'industrie. Dès les premières années de sa carrière, elle a été une présence régulière sur des plateformes de renom. Ces partenariats précoces lui ont permis d'acquérir une visibilité rapide et de se bâtir une solide réputation en tant qu'interprète polyvalente.

Son évolution l'a ensuite amenée à diversifier ses rôles et à travailler avec d'autres studios influents. Elle a su s'adapter à différents types de scènes, démontrant une gamme de performances qui ont plu à un large public. Bien que sa carrière en scènes explicites ait connu son apogée autour de {metadata.get('peak_years', '[période]')}, sa vaste filmographie et la qualité constante de ses prestations lui ont assuré une place de choix parmi les étoiles de sa génération.

**💡 Faits Intéressants & Vie Personnelle**
Au-delà de l'écran, {performer_name} est réputée pour sa personnalité authentique et son approche terre-à-terre. La sphère de sa vie personnelle reste, comme il est courant dans cette industrie, relativement privée. {metadata.get('trivia', '')}

**👗 Apparence et Style**
{performer_name} est souvent caractérisée par une beauté distinctive, ancrée dans ses origines {metadata.get('ethnicity', '[origine]')}. Elle arbore typiquement une chevelure {metadata.get('hair_color', '[couleur]')}, souvent longue et soyeuse, qui encadre un visage expressif et une silhouette généralement {metadata.get('body_type', 'fine et athlétique')}. Son style sur scène est marqué par une énergie palpable et une capacité à incarner des personnages variés avec crédibilité.

Mesures physiques : {metadata.get('measurements', '[mesures]')} - Taille : {metadata.get('height', '[taille]')} - Poids : {metadata.get('weight', '[poids]')}
Tatouages : {metadata.get('tattoos', 'Information non disponible')}
Piercings : {metadata.get('piercings', 'Information non disponible')}

**🏆 Prix et Distinctions**
La reconnaissance de l'industrie n'a pas tardé à se manifester pour {performer_name}, qui a été honorée de nombreuses nominations au cours de sa carrière. {metadata.get('awards_summary', '')}

**Conclusion rapide**
En somme, {performer_name} demeure une figure emblématique et respectée de l'industrie pour adultes. Son parcours, caractérisé par une entrée remarquée en {metadata.get('career_start', '[année]')} et une carrière diversifiée sous plusieurs alias, a laissé une impression durable. Son professionnalisme, son charme et sa capacité à captiver le public continuent d'être salués par ses fans et les connaisseurs du milieu, confirmant son statut d'étoile marquante de sa génération."""
        
        # Limiter à environ 3000 caractères
        if len(template) > 3000:
            # Couper intelligemment
            template = template[:2950] + "..."
        
        return template
    
    def generate_ollama_bio(self, performer_name: str, metadata: Dict, custom_prompt: str = "") -> Optional[str]:
        """Génère une bio avec Ollama"""
        try:
            # Construire le prompt
            if custom_prompt:
                prompt = custom_prompt
            else:
                prompt = f"""Écris une biographie professionnelle de 3000 caractères pour {performer_name}, 
                actrice de l'industrie du divertissement pour adultes.
                
                Informations disponibles :
                - Nom : {performer_name}
                - Aliases : {', '.join(metadata.get('aliases', []))}
                - Date de naissance : {metadata.get('birthdate', 'Non disponible')}
                - Lieu de naissance : {metadata.get('birthplace', 'Non disponible')}
                - Ethnicité : {metadata.get('ethnicity', 'Non disponible')}
                - Début de carrière : {metadata.get('career_start', 'Non disponible')}
                - Mesures : {metadata.get('measurements', 'Non disponible')}
                
                La biographie doit être :
                - Professionnelle et respectueuse
                - Structurée avec des sections claires
                - D'environ 3000 caractères
                - En français
                """
            
            # Appel à Ollama
            response = requests.post(
                self.ollama_url,
                json={
                    "model": "llama2",
                    "prompt": prompt,
                    "stream": False
                },
                timeout=120
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get('response', '')
            else:
                return None
        except Exception as e:
            print(f"Erreur Ollama: {e}")
            return None


class TriviaAwardsWindow(tk.Toplevel):
    """Fenêtre séparée pour Trivia et Awards avec requête et résultats"""
    
    def __init__(self, parent, performer_name: str, urls: List[str]):
        super().__init__(parent)
        self.title(f"Trivia & Awards — {performer_name}")
        self.geometry("1000x700")
        
        self.performer_name = performer_name
        self.urls = urls
        self.awards_cleaner = AwardsCleaner()
        
        self._create_widgets()
    
    def _create_widgets(self):
        # Frame principal
        main_frame = ttk.Frame(self, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(2, weight=1)
        main_frame.rowconfigure(4, weight=1)
        
        # Section Trivia
        trivia_label = ttk.Label(main_frame, text="📝 Trivia", font=('Segoe UI', 12, 'bold'))
        trivia_label.grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        
        # Boutons de scraping pour Trivia
        trivia_btn_frame = ttk.Frame(main_frame)
        trivia_btn_frame.grid(row=1, column=0, sticky=tk.W, pady=(0, 5))
        
        ttk.Button(trivia_btn_frame, text="Scraper Trivia", 
                   command=self._scrape_trivia).pack(side=tk.LEFT, padx=(0, 5))
        
        # Champ Trivia (multiligne)
        self.trivia_text = scrolledtext.ScrolledText(main_frame, height=8, wrap=tk.WORD)
        self.trivia_text.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        # Section Awards
        awards_label = ttk.Label(main_frame, text="🏆 Awards & Nominations", 
                                 font=('Segoe UI', 12, 'bold'))
        awards_label.grid(row=3, column=0, sticky=tk.W, pady=(10, 5))
        
        # Boutons de scraping pour Awards
        awards_btn_frame = ttk.Frame(main_frame)
        awards_btn_frame.grid(row=4, column=0, sticky=tk.W, pady=(0, 5))
        
        ttk.Button(awards_btn_frame, text="Scraper Awards", 
                   command=self._scrape_awards).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(awards_btn_frame, text="Nettoyer Awards", 
                   command=self._clean_awards).pack(side=tk.LEFT, padx=(0, 5))
        
        # Champ Awards (multiligne)
        self.awards_text = scrolledtext.ScrolledText(main_frame, height=15, wrap=tk.WORD)
        self.awards_text.grid(row=5, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        # Boutons d'action
        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=6, column=0, sticky=tk.E, pady=(10, 0))
        
        ttk.Button(btn_frame, text="Annuler", command=self.destroy).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(btn_frame, text="Appliquer et continuer", 
                   command=self._apply_and_continue).pack(side=tk.LEFT)
    
    def _scrape_trivia(self):
        """Scrape les trivia depuis les URLs"""
        self.trivia_text.delete('1.0', tk.END)
        self.trivia_text.insert('1.0', "Scraping en cours...\n")
        
        def scrape():
            trivia_items = []
            for url in self.urls:
                if 'iafd.com' in url:
                    trivia = self._scrape_iafd_trivia(url)
                    if trivia:
                        trivia_items.extend(trivia)
            
            # Afficher les résultats
            self.after(0, lambda: self._display_trivia(trivia_items))
        
        thread = threading.Thread(target=scrape)
        thread.daemon = True
        thread.start()
    
    def _scrape_iafd_trivia(self, url: str) -> List[str]:
        """Scrape les trivia depuis IAFD"""
        try:
            response = requests.get(url, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Chercher la section trivia (à adapter selon la structure réelle)
            trivia = []
            # Code de scraping à adapter selon la structure du site
            
            return trivia
        except Exception as e:
            print(f"Erreur scraping trivia: {e}")
            return []
    
    def _display_trivia(self, trivia_items: List[str]):
        """Affiche les trivia scrapés"""
        self.trivia_text.delete('1.0', tk.END)
        if trivia_items:
            for item in trivia_items:
                self.trivia_text.insert(tk.END, f"• {item}\n")
        else:
            self.trivia_text.insert(tk.END, "Aucun trivia trouvé.")
    
    def _scrape_awards(self):
        """Scrape les awards depuis les URLs"""
        self.awards_text.delete('1.0', tk.END)
        self.awards_text.insert('1.0', "Scraping en cours...\n")
        
        def scrape():
            awards_text = ""
            for url in self.urls:
                if 'iafd.com' in url:
                    awards = self._scrape_iafd_awards(url)
                    if awards:
                        awards_text += awards + "\n\n"
            
            # Afficher les résultats
            self.after(0, lambda: self._display_awards(awards_text))
        
        thread = threading.Thread(target=scrape)
        thread.daemon = True
        thread.start()
    
    def _scrape_iafd_awards(self, url: str) -> str:
        """Scrape les awards depuis IAFD"""
        try:
            response = requests.get(url, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Chercher la section awards (à adapter selon la structure réelle)
            awards = ""
            # Code de scraping à adapter
            
            return awards
        except Exception as e:
            print(f"Erreur scraping awards: {e}")
            return ""
    
    def _display_awards(self, awards_text: str):
        """Affiche les awards scrapés"""
        self.awards_text.delete('1.0', tk.END)
        if awards_text:
            self.awards_text.insert(tk.END, awards_text)
        else:
            self.awards_text.insert(tk.END, "Aucun award trouvé.")
    
    def _clean_awards(self):
        """Nettoie les awards pour avoir 1 par ligne"""
        raw_text = self.awards_text.get('1.0', tk.END)
        cleaned_text = self.awards_cleaner.clean_awards(raw_text)
        self.awards_text.delete('1.0', tk.END)
        self.awards_text.insert('1.0', cleaned_text)
    
    def _apply_and_continue(self):
        """Applique les modifications et ferme la fenêtre"""
        # Récupérer les données
        self.trivia_data = self.trivia_text.get('1.0', tk.END).strip()
        self.awards_data = self.awards_text.get('1.0', tk.END).strip()
        self.destroy()
    
    def get_data(self) -> Dict:
        """Retourne les données collectées"""
        return {
            'trivia': getattr(self, 'trivia_data', ''),
            'awards': getattr(self, 'awards_data', '')
        }


class BioGenerationWindow(tk.Toplevel):
    """Fenêtre pour la génération de bio"""
    
    def __init__(self, parent, performer_name: str, metadata: Dict):
        super().__init__(parent)
        self.title(f"Génération de Bio — {performer_name}")
        self.geometry("900x800")
        
        self.performer_name = performer_name
        self.metadata = metadata
        self.bio_generator = BioGenerator()
        
        self._create_widgets()
    
    def _create_widgets(self):
        # Frame principal
        main_frame = ttk.Frame(self, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(3, weight=1)
        
        # Options de génération
        options_frame = ttk.LabelFrame(main_frame, text="Options de génération", padding="10")
        options_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        options_frame.columnconfigure(1, weight=1)
        
        # Choix du type de bio
        self.bio_type_var = tk.StringVar(value="google")
        
        ttk.Radiobutton(options_frame, text="Bio Google (3000 car. automatique)", 
                        variable=self.bio_type_var, value="google").grid(row=0, column=0, sticky=tk.W)
        
        ttk.Radiobutton(options_frame, text="Bio Ollama (avec IA locale)", 
                        variable=self.bio_type_var, value="ollama").grid(row=1, column=0, sticky=tk.W)
        
        ttk.Radiobutton(options_frame, text="Bio Ollama avec prompt personnalisé", 
                        variable=self.bio_type_var, value="ollama_custom").grid(row=2, column=0, sticky=tk.W)
        
        # Section prompt personnalisé
        prompt_frame = ttk.LabelFrame(main_frame, text="Prompt personnalisé (optionnel)", padding="10")
        prompt_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        prompt_frame.columnconfigure(0, weight=1)
        prompt_frame.rowconfigure(1, weight=1)
        
        ttk.Label(prompt_frame, text="Entrez vos directives précises pour la génération de la bio :").grid(
            row=0, column=0, sticky=tk.W, pady=(0, 5))
        
        self.prompt_text = scrolledtext.ScrolledText(prompt_frame, height=6, wrap=tk.WORD)
        self.prompt_text.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Bouton de génération
        ttk.Button(main_frame, text="Générer la Bio", 
                   command=self._generate_bio).grid(row=2, column=0, pady=(0, 10))
        
        # Résultat
        result_frame = ttk.LabelFrame(main_frame, text="Bio générée", padding="10")
        result_frame.grid(row=3, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        result_frame.columnconfigure(0, weight=1)
        result_frame.rowconfigure(0, weight=1)
        
        self.bio_text = scrolledtext.ScrolledText(result_frame, wrap=tk.WORD)
        self.bio_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Label pour le compteur de caractères
        self.char_count_label = ttk.Label(result_frame, text="Caractères : 0")
        self.char_count_label.grid(row=1, column=0, sticky=tk.E, pady=(5, 0))
        
        # Boutons d'action
        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=4, column=0, sticky=tk.E, pady=(10, 0))
        
        ttk.Button(btn_frame, text="Annuler", command=self.destroy).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(btn_frame, text="Appliquer", 
                   command=self._apply_bio).pack(side=tk.LEFT)
    
    def _generate_bio(self):
        """Génère la bio selon le type choisi"""
        bio_type = self.bio_type_var.get()
        
        self.bio_text.delete('1.0', tk.END)
        self.bio_text.insert('1.0', "Génération en cours...\n")
        
        def generate():
            bio = ""
            if bio_type == "google":
                bio = self.bio_generator.generate_google_bio(self.performer_name, self.metadata)
            elif bio_type in ["ollama", "ollama_custom"]:
                custom_prompt = ""
                if bio_type == "ollama_custom":
                    custom_prompt = self.prompt_text.get('1.0', tk.END).strip()
                bio = self.bio_generator.generate_ollama_bio(
                    self.performer_name, self.metadata, custom_prompt)
                if bio is None:
                    bio = "Erreur: Ollama n'est pas disponible ou n'a pas répondu."
            
            # Afficher le résultat
            self.after(0, lambda: self._display_bio(bio))
        
        thread = threading.Thread(target=generate)
        thread.daemon = True
        thread.start()
    
    def _display_bio(self, bio: str):
        """Affiche la bio générée"""
        self.bio_text.delete('1.0', tk.END)
        self.bio_text.insert('1.0', bio)
        
        # Mettre à jour le compteur de caractères
        char_count = len(bio)
        self.char_count_label.config(text=f"Caractères : {char_count}")
    
    def _apply_bio(self):
        """Applique la bio et ferme la fenêtre"""
        self.generated_bio = self.bio_text.get('1.0', tk.END).strip()
        self.destroy()
    
    def get_bio(self) -> str:
        """Retourne la bio générée"""
        return getattr(self, 'generated_bio', '')


class MainWindow(tk.Tk):
    """Fenêtre principale unifiée - Fusion Phase 1 et Phase 2"""
    
    def __init__(self):
        super().__init__()
        
        self.title("StashMaster V2 - Performer")
        self.geometry("1200x900")
        
        self.tag_rules = TagRulesEngine()
        self.metadata = {}
        
        self._create_widgets()
        self._create_menu()
    
    def _create_menu(self):
        """Crée le menu principal"""
        menubar = tk.Menu(self)
        self.config(menu=menubar)
        
        # Menu Fichier
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Fichier", menu=file_menu)
        file_menu.add_command(label="Nouveau", command=self._new_performer)
        file_menu.add_command(label="Ouvrir...", command=self._open_performer)
        file_menu.add_separator()
        file_menu.add_command(label="Quitter", command=self.quit)
        
        # Menu Actions
        actions_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Actions", menu=actions_menu)
        actions_menu.add_command(label="Scraper & Lancer le flux Bio IA", 
                                 command=self._start_scraping)
        actions_menu.add_command(label="Trivia & Awards...", 
                                 command=self._open_trivia_awards)
        actions_menu.add_command(label="Générer Bio...", 
                                 command=self._open_bio_generator)
    
    def _create_widgets(self):
        """Crée l'interface principale"""
        # Notebook pour les onglets
        notebook = ttk.Notebook(self)
        notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Onglet 1: Métadonnées usuelles
        self.metadata_frame = self._create_metadata_tab()
        notebook.add(self.metadata_frame, text="📋 Métadonnées")
        
        # Onglet 2: Champs avancés
        self.advanced_frame = self._create_advanced_tab()
        notebook.add(self.advanced_frame, text="⚙️ Champs Avancés")
        
        # Onglet 3: Bio
        self.bio_frame = self._create_bio_tab()
        notebook.add(self.bio_frame, text="📝 Bio")
        
        # Barre d'outils en bas
        self._create_toolbar()
    
    def _create_metadata_tab(self) -> ttk.Frame:
        """Crée l'onglet des métadonnées de base"""
        frame = ttk.Frame()
        
        # Frame avec scrollbar
        canvas = tk.Canvas(frame)
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Champs de métadonnées
        fields = [
            ("Name:", "name"),
            ("Aliases:", "aliases"),
            ("Birthdate:", "birthdate"),
            ("Deathdate:", "deathdate"),
            ("Country:", "country"),
            ("Ethnicity:", "ethnicity"),
            ("Hair Color:", "hair_color"),
            ("Eye Color:", "eye_color"),
            ("Height:", "height"),
            ("Weight:", "weight"),
            ("Measurements:", "measurements"),
            ("Fake Tits:", "fake_tits"),
            ("Career Length:", "career_length"),
        ]
        
        self.metadata_entries = {}
        
        for i, (label, key) in enumerate(fields):
            ttk.Label(scrollable_frame, text=label).grid(row=i, column=0, sticky=tk.W, 
                                                          padx=5, pady=3)
            entry = ttk.Entry(scrollable_frame, width=50)
            entry.grid(row=i, column=1, sticky=(tk.W, tk.E), padx=5, pady=3)
            self.metadata_entries[key] = entry
        
        scrollable_frame.columnconfigure(1, weight=1)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        return frame
    
    def _create_advanced_tab(self) -> ttk.Frame:
        """Crée l'onglet des champs avancés"""
        frame = ttk.Frame()
        frame.columnconfigure(0, weight=1)
        
        row = 0
        
        # Tags - CHAMP SIMPLE LIGNE (générés automatiquement)
        ttk.Label(frame, text="Tags (générés automatiquement):", 
                  font=('Segoe UI', 10, 'bold')).grid(row=row, column=0, sticky=tk.W, 
                                                       padx=5, pady=(10, 2))
        row += 1
        
        self.tags_entry = ttk.Entry(frame, state='readonly')
        self.tags_entry.grid(row=row, column=0, sticky=(tk.W, tk.E), padx=5, pady=(0, 10))
        row += 1
        
        # Piercings - CHAMP MULTILIGNE
        ttk.Label(frame, text="Piercings:", 
                  font=('Segoe UI', 10, 'bold')).grid(row=row, column=0, sticky=tk.W, 
                                                       padx=5, pady=(10, 2))
        row += 1
        
        self.piercings_text = scrolledtext.ScrolledText(frame, height=4, wrap=tk.WORD)
        self.piercings_text.grid(row=row, column=0, sticky=(tk.W, tk.E), padx=5, pady=(0, 10))
        row += 1
        
        # Tattoos - CHAMP MULTILIGNE
        ttk.Label(frame, text="Tattoos:", 
                  font=('Segoe UI', 10, 'bold')).grid(row=row, column=0, sticky=tk.W, 
                                                       padx=5, pady=(10, 2))
        row += 1
        
        self.tattoos_text = scrolledtext.ScrolledText(frame, height=4, wrap=tk.WORD)
        self.tattoos_text.grid(row=row, column=0, sticky=(tk.W, tk.E), padx=5, pady=(0, 10))
        row += 1
        
        # URLs - CHAMP MULTILIGNE
        ttk.Label(frame, text="URLs:", 
                  font=('Segoe UI', 10, 'bold')).grid(row=row, column=0, sticky=tk.W, 
                                                       padx=5, pady=(10, 2))
        row += 1
        
        self.urls_text = scrolledtext.ScrolledText(frame, height=6, wrap=tk.WORD)
        self.urls_text.grid(row=row, column=0, sticky=(tk.W, tk.E), padx=5, pady=(0, 10))
        row += 1
        
        # Bouton pour générer les tags
        ttk.Button(frame, text="🔄 Générer Tags", 
                   command=self._generate_tags).grid(row=row, column=0, pady=10)
        
        return frame
    
    def _create_bio_tab(self) -> ttk.Frame:
        """Crée l'onglet de la bio"""
        frame = ttk.Frame()
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(1, weight=1)
        
        # Boutons d'action
        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        
        ttk.Button(btn_frame, text="📝 Générer Bio...", 
                   command=self._open_bio_generator).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(btn_frame, text="🗑️ Effacer", 
                   command=self._clear_bio).pack(side=tk.LEFT)
        
        # Champ de bio
        self.bio_text = scrolledtext.ScrolledText(frame, wrap=tk.WORD)
        self.bio_text.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), 
                          padx=5, pady=(0, 5))
        
        # Compteur de caractères
        self.bio_char_label = ttk.Label(frame, text="Caractères : 0")
        self.bio_char_label.grid(row=2, column=0, sticky=tk.E, padx=5, pady=(0, 5))
        
        # Binding pour mettre à jour le compteur
        self.bio_text.bind('<KeyRelease>', self._update_bio_char_count)
        
        return frame
    
    def _create_toolbar(self):
        """Crée la barre d'outils en bas"""
        toolbar = ttk.Frame(self)
        toolbar.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=5)
        
        ttk.Button(toolbar, text="Tout sélectionner", 
                   command=self._select_all).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(toolbar, text="Sélectionner vidéos", 
                   command=self._select_videos).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(toolbar, text="Suivant / Traiter", 
                   command=self._process_next).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(toolbar, text="Retour", 
                   command=self._go_back).pack(side=tk.LEFT)
        
        # Spacer
        ttk.Frame(toolbar).pack(side=tk.LEFT, expand=True)
        
        ttk.Button(toolbar, text="💾 Sauvegarder", 
                   command=self._save).pack(side=tk.RIGHT, padx=(5, 0))
    
    def _generate_tags(self):
        """Génère les tags automatiquement basés sur les métadonnées"""
        # Récupérer les métadonnées actuelles
        metadata = {
            'ethnicity': self.metadata_entries['ethnicity'].get(),
            'hair_color': self.metadata_entries['hair_color'].get(),
            'measurements': self.metadata_entries['measurements'].get(),
            'piercings': self.piercings_text.get('1.0', tk.END).strip(),
            'tattoos': self.tattoos_text.get('1.0', tk.END).strip(),
            'career_length': self.metadata_entries['career_length'].get(),
        }
        
        # Générer les tags
        tags = self.tag_rules.generate_tags(metadata)
        
        # Afficher les tags
        self.tags_entry.config(state='normal')
        self.tags_entry.delete(0, tk.END)
        self.tags_entry.insert(0, ', '.join(tags))
        self.tags_entry.config(state='readonly')
        
        messagebox.showinfo("Tags générés", 
                           f"{len(tags)} tag(s) généré(s) automatiquement.")
    
    def _update_bio_char_count(self, event=None):
        """Met à jour le compteur de caractères de la bio"""
        text = self.bio_text.get('1.0', tk.END)
        count = len(text.strip())
        self.bio_char_label.config(text=f"Caractères : {count}")
    
    def _clear_bio(self):
        """Efface la bio"""
        if messagebox.askyesno("Confirmation", 
                              "Êtes-vous sûr de vouloir effacer la bio ?"):
            self.bio_text.delete('1.0', tk.END)
            self._update_bio_char_count()
    
    def _start_scraping(self):
        """Lance le flux de scraping complet"""
        messagebox.showinfo("Scraping", 
                           "Fonction de scraping à implémenter...")
    
    def _open_trivia_awards(self):
        """Ouvre la fenêtre Trivia & Awards"""
        # Récupérer le nom et les URLs
        performer_name = self.metadata_entries['name'].get()
        if not performer_name:
            messagebox.showwarning("Attention", "Veuillez entrer un nom de performer.")
            return
        
        urls_text = self.urls_text.get('1.0', tk.END).strip()
        urls = [url.strip() for url in urls_text.split('\n') if url.strip()]
        
        if not urls:
            messagebox.showwarning("Attention", "Veuillez entrer au moins une URL.")
            return
        
        # Ouvrir la fenêtre
        window = TriviaAwardsWindow(self, performer_name, urls)
        self.wait_window(window)
        
        # Récupérer les données
        data = window.get_data()
        # Stocker dans les métadonnées
        self.metadata['trivia'] = data.get('trivia', '')
        self.metadata['awards'] = data.get('awards', '')
        
        messagebox.showinfo("Trivia & Awards", 
                           "Données collectées avec succès.")
    
    def _open_bio_generator(self):
        """Ouvre la fenêtre de génération de bio"""
        # Récupérer le nom
        performer_name = self.metadata_entries['name'].get()
        if not performer_name:
            messagebox.showwarning("Attention", "Veuillez entrer un nom de performer.")
            return
        
        # Préparer les métadonnées
        metadata = {
            'name': performer_name,
            'aliases': self.metadata_entries['aliases'].get().split(','),
            'birthdate': self.metadata_entries['birthdate'].get(),
            'birthplace': self.metadata_entries['country'].get(),
            'ethnicity': self.metadata_entries['ethnicity'].get(),
            'hair_color': self.metadata_entries['hair_color'].get(),
            'measurements': self.metadata_entries['measurements'].get(),
            'height': self.metadata_entries['height'].get(),
            'weight': self.metadata_entries['weight'].get(),
            'tattoos': self.tattoos_text.get('1.0', tk.END).strip(),
            'piercings': self.piercings_text.get('1.0', tk.END).strip(),
            'trivia': self.metadata.get('trivia', ''),
            'awards': self.metadata.get('awards', ''),
            'career_length': self.metadata_entries['career_length'].get(),
        }
        
        # Ouvrir la fenêtre
        window = BioGenerationWindow(self, performer_name, metadata)
        self.wait_window(window)
        
        # Récupérer la bio générée
        bio = window.get_bio()
        if bio:
            self.bio_text.delete('1.0', tk.END)
            self.bio_text.insert('1.0', bio)
            self._update_bio_char_count()
            messagebox.showinfo("Bio générée", "La bio a été générée avec succès.")
    
    def _new_performer(self):
        """Nouveau performer"""
        # Effacer tous les champs
        for entry in self.metadata_entries.values():
            entry.delete(0, tk.END)
        self.piercings_text.delete('1.0', tk.END)
        self.tattoos_text.delete('1.0', tk.END)
        self.urls_text.delete('1.0', tk.END)
        self.bio_text.delete('1.0', tk.END)
        self.tags_entry.config(state='normal')
        self.tags_entry.delete(0, tk.END)
        self.tags_entry.config(state='readonly')
        self.metadata = {}
    
    def _open_performer(self):
        """Ouvre un performer existant"""
        messagebox.showinfo("Ouvrir", "Fonction à implémenter...")
    
    def _select_all(self):
        """Sélectionne tous les champs"""
        pass
    
    def _select_videos(self):
        """Sélectionne les vidéos"""
        pass
    
    def _process_next(self):
        """Traite le performer suivant"""
        pass
    
    def _go_back(self):
        """Retour"""
        pass
    
    def _save(self):
        """Sauvegarde les données"""
        messagebox.showinfo("Sauvegarde", "Données sauvegardées (à implémenter).")


def main():
    app = MainWindow()
    app.mainloop()


if __name__ == "__main__":
    main()

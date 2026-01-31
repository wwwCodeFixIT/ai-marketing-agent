#!/usr/bin/env python3
"""
AI Marketing Agent - CLI Generator
Generuj posty z linii poleceń z pełnym pipeline'em agenta.

Użycie:
    python generator.py "Twój temat tutaj"
    python generator.py "Temat" --platform linkedin --style professional
    python generator.py "Temat" --all-platforms --quick
    python generator.py "Temat" --output markdown
"""

import os
import sys
import argparse
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv

# Import modułów core
from core.memory_system import BrandMemory, FeedbackManager, PostsHistory
from core.prompt_builder import Platform, ContentGoal, ContentStyle
from core.model_router import ModelRouter
from core.agent_engine import AgentEngine, AgentResult

# Konfiguracja
load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Kolory terminala
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'


def print_header():
    """Wyświetla header aplikacji"""
    print(f"""
{Colors.CYAN}{Colors.BOLD}
    ╔═══════════════════════════════════════════════════════════╗
    ║                                                           ║
    ║   🧠  AI MARKETING AGENT  v2.0                           ║
    ║                                                           ║
    ║   Multi-step reasoning • Self-critique • Brand DNA       ║
    ║                                                           ║
    ╚═══════════════════════════════════════════════════════════╝
{Colors.END}
""")


def print_step(emoji: str, message: str, color: str = Colors.CYAN):
    """Wyświetla krok procesu"""
    print(f"{color}{emoji} {message}{Colors.END}")


def print_success(message: str):
    """Wyświetla sukces"""
    print(f"{Colors.GREEN}✅ {message}{Colors.END}")


def print_error(message: str):
    """Wyświetla błąd"""
    print(f"{Colors.RED}❌ {message}{Colors.END}")


def print_log(log: str):
    """Wyświetla log agenta"""
    # Kolorowanie na podstawie emoji
    if "✅" in log or "🎉" in log:
        color = Colors.GREEN
    elif "⚠️" in log or "🧐" in log:
        color = Colors.YELLOW
    elif "❌" in log:
        color = Colors.RED
    else:
        color = Colors.CYAN
    
    print(f"   {color}{log}{Colors.END}")


def validate_api_key() -> bool:
    """Sprawdza czy klucz API jest dostępny"""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        print_error("Brak klucza GROQ_API_KEY!")
        print(f"\n   Utwórz plik {Colors.YELLOW}.env{Colors.END} z zawartością:")
        print(f"   {Colors.CYAN}GROQ_API_KEY=gsk_twoj_klucz_tutaj{Colors.END}\n")
        return False
    return True


def parse_platform(platform_str: str) -> Platform:
    """Parsuje string do Platform enum"""
    mapping = {
        "linkedin": Platform.LINKEDIN,
        "twitter": Platform.TWITTER,
        "facebook": Platform.FACEBOOK,
        "instagram": Platform.INSTAGRAM,
        "threads": Platform.THREADS
    }
    return mapping.get(platform_str.lower(), Platform.LINKEDIN)


def parse_goal(goal_str: str) -> ContentGoal:
    """Parsuje string do ContentGoal enum"""
    mapping = {
        "engagement": ContentGoal.ENGAGEMENT,
        "authority": ContentGoal.AUTHORITY,
        "viral": ContentGoal.VIRAL,
        "conversion": ContentGoal.CONVERSION,
        "education": ContentGoal.EDUCATION,
        "storytelling": ContentGoal.STORYTELLING
    }
    return mapping.get(goal_str.lower(), ContentGoal.ENGAGEMENT)


def parse_style(style_str: str) -> ContentStyle:
    """Parsuje string do ContentStyle enum"""
    mapping = {
        "professional": ContentStyle.PROFESSIONAL,
        "casual": ContentStyle.CASUAL,
        "controversial": ContentStyle.CONTROVERSIAL,
        "inspirational": ContentStyle.INSPIRATIONAL,
        "analytical": ContentStyle.ANALYTICAL,
        "humorous": ContentStyle.HUMOROUS
    }
    return mapping.get(style_str.lower(), ContentStyle.PROFESSIONAL)


def save_markdown(
    topic: str,
    results: dict,
    output_dir: Path
) -> Path:
    """Zapisuje wyniki do pliku Markdown"""
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_topic = "".join([c if c.isalnum() else "_" for c in topic])[:30]
    filename = f"campaign_{timestamp}_{safe_topic}.md"
    filepath = output_dir / filename
    
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(f"# 🧠 AI Marketing Agent - Raport\n\n")
        f.write(f"**Data:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"**Temat:** {topic}\n\n")
        f.write("---\n\n")
        
        for platform, result in results.items():
            f.write(f"## 📱 {platform}\n\n")
            
            # Metryki
            if result.state:
                f.write(f"**Metryki:**\n")
                f.write(f"- ⏱️ Czas: {result.state.total_duration_ms}ms\n")
                f.write(f"- 🔄 Iteracje: {result.state.iterations}\n")
                f.write(f"- 📊 Ocena: {result.state.critique_score}/10\n")
                f.write(f"- 🛡️ Brand: {'✅ Zgodny' if result.state.brand_approved else '⚠️ Wymaga uwagi'}\n\n")
            
            # Treść
            f.write(f"### Treść\n\n")
            f.write(f"```\n{result.content}\n```\n\n")
            
            # Logi agenta
            f.write(f"### Proces agenta\n\n")
            for log in result.get_logs_formatted():
                f.write(f"- {log}\n")
            
            f.write("\n---\n\n")
    
    return filepath


def save_json(
    topic: str,
    results: dict,
    output_dir: Path
) -> Path:
    """Zapisuje wyniki do pliku JSON"""
    import json
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_topic = "".join([c if c.isalnum() else "_" for c in topic])[:30]
    filename = f"campaign_{timestamp}_{safe_topic}.json"
    filepath = output_dir / filename
    
    data = {
        "timestamp": datetime.now().isoformat(),
        "topic": topic,
        "results": {}
    }
    
    for platform, result in results.items():
        data["results"][platform] = {
            "success": result.success,
            "content": result.content,
            "metrics": {
                "duration_ms": result.state.total_duration_ms if result.state else 0,
                "iterations": result.state.iterations if result.state else 0,
                "score": result.state.critique_score if result.state else 0,
                "brand_approved": result.state.brand_approved if result.state else False
            },
            "logs": result.get_logs_formatted()
        }
    
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    return filepath


def run_generation(
    topic: str,
    platforms: List[Platform],
    goal: ContentGoal,
    style: ContentStyle,
    quick_mode: bool = False,
    show_logs: bool = True
) -> dict:
    """Uruchamia generowanie dla wszystkich platform"""
    
    # Inicjalizacja
    router = ModelRouter()
    brand_memory = BrandMemory()
    feedback_manager = FeedbackManager()
    posts_history = PostsHistory()
    
    engine = AgentEngine(
        router=router,
        brand_memory=brand_memory,
        feedback_manager=feedback_manager,
        posts_history=posts_history
    )
    
    results = {}
    
    print_step("🚀", f"Uruchamiam agenta (Model: {router.get_available_models()[0].display_name if router.get_available_models() else 'N/A'})")
    print_step("📝", f"Temat: {topic[:60]}{'...' if len(topic) > 60 else ''}")
    print_step("🎯", f"Cel: {goal.value} | Styl: {style.value}")
    print()
    
    for platform in platforms:
        print_step("📱", f"Generuję dla: {platform.value}", Colors.YELLOW)
        
        if quick_mode:
            result = engine.run_quick(
                topic=topic,
                platform=platform,
                style=style
            )
        else:
            result = engine.run_pipeline(
                topic=topic,
                platform=platform,
                goal=goal,
                style=style
            )
        
        results[platform.value] = result
        
        # Pokaż logi
        if show_logs:
            for log in result.get_logs_formatted():
                print_log(log)
        
        # Pokaż wynik
        if result.success:
            print_success(f"{platform.value} - Gotowe!")
            if result.state:
                print(f"   📊 Ocena: {result.state.critique_score}/10 | ⏱️ {result.state.total_duration_ms}ms")
        else:
            print_error(f"{platform.value} - Błąd: {result.error}")
        
        print()
    
    return results


def display_results(results: dict):
    """Wyświetla wyniki w terminalu"""
    
    print(f"\n{Colors.BOLD}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}📄 WYGENEROWANE TREŚCI{Colors.END}")
    print(f"{Colors.BOLD}{'='*60}{Colors.END}\n")
    
    for platform, result in results.items():
        print(f"{Colors.CYAN}{Colors.BOLD}▶ {platform}{Colors.END}")
        print(f"{Colors.CYAN}{'─'*40}{Colors.END}")
        
        if result.success:
            # Wyświetl content
            lines = result.content.split('\n')
            for line in lines:
                print(f"  {line}")
        else:
            print(f"  {Colors.RED}Błąd: {result.error}{Colors.END}")
        
        print()


def main():
    """Główna funkcja CLI"""
    
    # Parser argumentów
    parser = argparse.ArgumentParser(
        description="AI Marketing Agent - CLI Generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Przykłady użycia:
  python generator.py "Dlaczego code review to inwestycja"
  python generator.py "Temat" --platform twitter --style casual
  python generator.py "Temat" --all-platforms --quick
  python generator.py "Temat" -p linkedin -p twitter --goal viral
  python generator.py "Temat" --output json --no-logs
        """
    )
    
    parser.add_argument(
        "topic",
        help="Temat / pomysł na post"
    )
    
    parser.add_argument(
        "-p", "--platform",
        action="append",
        choices=["linkedin", "twitter", "facebook", "instagram", "threads"],
        help="Platforma (można podać wielokrotnie)"
    )
    
    parser.add_argument(
        "--all-platforms",
        action="store_true",
        help="Generuj dla wszystkich głównych platform"
    )
    
    parser.add_argument(
        "-g", "--goal",
        choices=["engagement", "authority", "viral", "conversion", "education", "storytelling"],
        default="engagement",
        help="Cel treści (domyślnie: engagement)"
    )
    
    parser.add_argument(
        "-s", "--style",
        choices=["professional", "casual", "controversial", "inspirational", "analytical", "humorous"],
        default="professional",
        help="Styl treści (domyślnie: professional)"
    )
    
    parser.add_argument(
        "-q", "--quick",
        action="store_true",
        help="Tryb szybki (bez pełnego pipeline'u)"
    )
    
    parser.add_argument(
        "-o", "--output",
        choices=["terminal", "markdown", "json", "all"],
        default="terminal",
        help="Format wyjścia (domyślnie: terminal)"
    )
    
    parser.add_argument(
        "--output-dir",
        type=str,
        default="outputs",
        help="Katalog wyjściowy dla plików"
    )
    
    parser.add_argument(
        "--no-logs",
        action="store_true",
        help="Nie pokazuj logów agenta"
    )
    
    parser.add_argument(
        "--no-header",
        action="store_true",
        help="Nie pokazuj headera"
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Tryb verbose (więcej informacji)"
    )
    
    args = parser.parse_args()
    
    # Header
    if not args.no_header:
        print_header()
    
    # Walidacja API key
    if not validate_api_key():
        sys.exit(1)
    
    # Ustal platformy
    if args.all_platforms:
        platforms = [Platform.LINKEDIN, Platform.TWITTER, Platform.FACEBOOK]
    elif args.platform:
        platforms = [parse_platform(p) for p in args.platform]
    else:
        platforms = [Platform.LINKEDIN]  # Domyślnie LinkedIn
    
    # Parsuj goal i style
    goal = parse_goal(args.goal)
    style = parse_style(args.style)
    
    # Verbose logging
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Uruchom generowanie
    try:
        results = run_generation(
            topic=args.topic,
            platforms=platforms,
            goal=goal,
            style=style,
            quick_mode=args.quick,
            show_logs=not args.no_logs
        )
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}⚠️ Przerwano przez użytkownika{Colors.END}")
        sys.exit(0)
    except Exception as e:
        print_error(f"Błąd krytyczny: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)
    
    # Wyświetl wyniki
    if args.output in ["terminal", "all"]:
        display_results(results)
    
    # Zapisz do plików
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)
    
    if args.output in ["markdown", "all"]:
        filepath = save_markdown(args.topic, results, output_dir)
        print_success(f"Zapisano Markdown: {filepath}")
    
    if args.output in ["json", "all"]:
        filepath = save_json(args.topic, results, output_dir)
        print_success(f"Zapisano JSON: {filepath}")
    
    # Podsumowanie
    successful = sum(1 for r in results.values() if r.success)
    total = len(results)
    
    print(f"\n{Colors.BOLD}{'='*60}{Colors.END}")
    print(f"{Colors.GREEN}✅ Zakończono: {successful}/{total} platform wygenerowanych pomyślnie{Colors.END}")
    print(f"{Colors.BOLD}{'='*60}{Colors.END}\n")


if __name__ == "__main__":
    main()
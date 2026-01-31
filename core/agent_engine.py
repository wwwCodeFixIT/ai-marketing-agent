"""
Agent Engine - Wieloetapowy silnik agenta AI
- Multi-step reasoning pipeline
- Self-critique i auto-poprawa
- Integracja z Memory System
- Structured output między krokami
"""

import json
import logging
import time
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, field
from enum import Enum

from .prompt_builder import (
    PromptBuilder, 
    PromptContext, 
    Platform, 
    ContentGoal, 
    ContentStyle
)
from .model_router import ModelRouter, TaskType, APIResponse
from .memory_system import BrandMemory, FeedbackManager, PostsHistory

logger = logging.getLogger(__name__)


class AgentStep(Enum):
    """Kroki pipeline'u agenta"""
    STRATEGY = "strategy"
    COPYWRITING = "copywriting"
    CRITIQUE = "critique"
    EDITING = "editing"
    BRAND_CHECK = "brand_check"
    FINAL = "final"


@dataclass
class AgentLog:
    """Pojedynczy log z procesu agenta"""
    step: AgentStep
    agent_name: str
    emoji: str
    message: str
    details: str = ""
    duration_ms: int = 0
    model_used: str = ""


@dataclass
class PipelineState:
    """Stan pipeline'u - przekazywany między krokami"""
    topic: str
    platform: Platform
    goal: ContentGoal
    style: ContentStyle
    
    # Wyniki poszczególnych kroków
    strategy: str = ""
    draft: str = ""
    critique: str = ""
    critique_score: float = 0.0
    edited_content: str = ""
    brand_check_result: str = ""
    brand_approved: bool = False
    
    # Finalna treść
    final_content: str = ""
    
    # Metadane
    iterations: int = 0
    total_duration_ms: int = 0


@dataclass
class AgentResult:
    """Wynik działania agenta"""
    success: bool
    content: str
    platform: str
    logs: List[AgentLog]
    state: PipelineState
    error: str = ""
    
    def get_logs_formatted(self) -> List[str]:
        """Zwraca logi jako sformatowane stringi"""
        formatted = []
        for log in self.logs:
            line = f"{log.emoji} {log.agent_name}: {log.message}"
            if log.duration_ms > 0:
                line += f" ({log.duration_ms}ms)"
            formatted.append(line)
        return formatted


class AgentEngine:
    """
    Główny silnik agenta.
    Orkiestruje wieloetapowy pipeline generowania treści.
    """
    
    # Konfiguracja agentów
    AGENTS = {
        "strategist": {
            "name": "Strategist",
            "emoji": "🎯",
            "task_type": TaskType.STRATEGY,
            "temperature": 0.5
        },
        "copywriter": {
            "name": "Copywriter", 
            "emoji": "✍️",
            "task_type": TaskType.CREATIVE_WRITING,
            "temperature": 0.8
        },
        "critic": {
            "name": "Critic",
            "emoji": "🧐",
            "task_type": TaskType.CRITIQUE,
            "temperature": 0.3
        },
        "editor": {
            "name": "Editor",
            "emoji": "🛠️",
            "task_type": TaskType.EDITING,
            "temperature": 0.6
        },
        "brand_guardian": {
            "name": "Brand Guardian",
            "emoji": "🛡️",
            "task_type": TaskType.CRITIQUE,
            "temperature": 0.3
        }
    }
    
    # Próg jakości (poniżej = wymaga poprawy)
    QUALITY_THRESHOLD = 7.0
    
    # Maksymalna liczba iteracji poprawek
    MAX_ITERATIONS = 2
    
    def __init__(
        self,
        router: ModelRouter = None,
        brand_memory: BrandMemory = None,
        feedback_manager: FeedbackManager = None,
        posts_history: PostsHistory = None
    ):
        self.router = router or ModelRouter()
        self.prompt_builder = PromptBuilder()
        self.brand_memory = brand_memory or BrandMemory()
        self.feedback_manager = feedback_manager or FeedbackManager()
        self.posts_history = posts_history or PostsHistory()
        
        logger.info("Agent Engine initialized")
    
    def _call_agent(
        self,
        agent_role: str,
        context: PromptContext,
        previous_output: str = None,
        critique: str = None
    ) -> Tuple[str, AgentLog, APIResponse]:
        """
        Wywołuje pojedynczego agenta.
        
        Returns:
            Tuple[content, log, response]
        """
        agent_config = self.AGENTS.get(agent_role, {})
        agent_name = agent_config.get("name", agent_role)
        emoji = agent_config.get("emoji", "🤖")
        task_type = agent_config.get("task_type", TaskType.CREATIVE_WRITING)
        temperature = agent_config.get("temperature", 0.7)
        
        start_time = time.time()
        
        # Buduj prompty
        system_prompt = self.prompt_builder.build_system_prompt(agent_role, context)
        user_prompt = self.prompt_builder.build_user_prompt(
            agent_role, 
            context, 
            previous_output, 
            critique
        )
        
        # Wywołaj model
        response = self.router.call_simple(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            task_type=task_type,
            temperature=temperature
        )
        
        duration = int((time.time() - start_time) * 1000)
        
        # Utwórz log
        if response.success:
            log = AgentLog(
                step=AgentStep[agent_role.upper()] if agent_role.upper() in AgentStep.__members__ else AgentStep.FINAL,
                agent_name=agent_name,
                emoji=emoji,
                message=f"Zakończono pomyślnie",
                details=response.content[:100] + "..." if len(response.content) > 100 else response.content,
                duration_ms=duration,
                model_used=response.model_used
            )
            return response.content, log, response
        else:
            log = AgentLog(
                step=AgentStep.FINAL,
                agent_name=agent_name,
                emoji="❌",
                message=f"Błąd: {response.error}",
                duration_ms=duration
            )
            return "", log, response
    
    def _extract_score(self, critique_text: str) -> float:
        """Wyciąga ocenę numeryczną z tekstu krytyki"""
        import re
        
        # Szukaj wzorców typu "7/10", "8 / 10", "Score: 7"
        patterns = [
            r'(\d+(?:\.\d+)?)\s*/\s*10',  # 7/10, 7.5/10
            r'score[:\s]+(\d+(?:\.\d+)?)',  # Score: 7
            r'ocena[:\s]+(\d+(?:\.\d+)?)',  # Ocena: 7
            r'^(\d+(?:\.\d+)?)/10',  # Na początku: 7/10
        ]
        
        for pattern in patterns:
            match = re.search(pattern, critique_text.lower())
            if match:
                try:
                    score = float(match.group(1))
                    return min(10.0, max(0.0, score))  # Clamp do 0-10
                except ValueError:
                    continue
        
        # Domyślna ocena jeśli nie znaleziono
        return 5.0
    
    def _check_brand_compliance(self, content: str, critique_result: str) -> Tuple[bool, str]:
        """
        Sprawdza czy treść jest zgodna z Brand DNA.
        
        Returns:
            Tuple[is_approved, issues_description]
        """
        # Szukaj słów kluczowych w odpowiedzi brand guardiana
        lower_result = critique_result.lower()
        
        # Negatywne markery
        negative_markers = [
            "nie jest zgodn",
            "narusza",
            "problem",
            "zakazane słow",
            "niezgodn"
        ]
        
        # Pozytywne markery
        positive_markers = [
            "zgodn",
            "ok",
            "zatwierdz",
            "brak problem",
            "spełnia"
        ]
        
        has_negative = any(marker in lower_result for marker in negative_markers)
        has_positive = any(marker in lower_result for marker in positive_markers)
        
        # Dodatkowo: sprawdź zakazane słowa bezpośrednio
        forbidden = self.brand_memory.dna.get("forbidden_words", [])
        content_lower = content.lower()
        found_forbidden = [word for word in forbidden if word.lower() in content_lower]
        
        if found_forbidden:
            return False, f"Znaleziono zakazane słowa: {', '.join(found_forbidden)}"
        
        if has_negative and not has_positive:
            return False, critique_result
        
        return True, ""
    
    def run_pipeline(
        self,
        topic: str,
        platform: Platform,
        goal: ContentGoal = ContentGoal.ENGAGEMENT,
        style: ContentStyle = ContentStyle.PROFESSIONAL,
        skip_brand_check: bool = False
    ) -> AgentResult:
        """
        Uruchamia pełny pipeline generowania treści.
        
        Pipeline:
        1. Strategist - analiza i określenie angle'u
        2. Copywriter - napisanie draftu
        3. Critic - ocena jakości
        4. Editor - poprawki (jeśli potrzebne)
        5. Brand Guardian - sprawdzenie zgodności
        6. Final Output
        """
        
        logs: List[AgentLog] = []
        start_time = time.time()
        
        # Inicjalizacja stanu
        state = PipelineState(
            topic=topic,
            platform=platform,
            goal=goal,
            style=style
        )
        
        # Przygotuj kontekst
        brand_context = self.brand_memory.get_prompt_context()
        learning_context = self.feedback_manager.get_learning_context(platform.value)
        
        context = PromptContext(
            topic=topic,
            platform=platform,
            goal=goal,
            style=style,
            brand_context=brand_context,
            learning_context=learning_context
        )
        
        try:
            # === KROK 1: STRATEGIST ===
            logs.append(AgentLog(
                step=AgentStep.STRATEGY,
                agent_name="Strategist",
                emoji="🎯",
                message="Analizuję cel i grupę docelową..."
            ))
            
            strategy, log, response = self._call_agent("strategist", context)
            logs.append(log)
            
            if not strategy:
                return AgentResult(
                    success=False,
                    content="",
                    platform=platform.value,
                    logs=logs,
                    state=state,
                    error="Strategist failed"
                )
            
            state.strategy = strategy
            logger.info(f"Strategy: {strategy[:100]}...")
            
            # === KROK 2: COPYWRITER ===
            logs.append(AgentLog(
                step=AgentStep.COPYWRITING,
                agent_name="Copywriter",
                emoji="✍️",
                message="Piszę pierwszą wersję..."
            ))
            
            draft, log, response = self._call_agent(
                "copywriter", 
                context, 
                previous_output=strategy
            )
            logs.append(log)
            
            if not draft:
                return AgentResult(
                    success=False,
                    content="",
                    platform=platform.value,
                    logs=logs,
                    state=state,
                    error="Copywriter failed"
                )
            
            state.draft = draft
            current_content = draft
            
            # === KROK 3: CRITIC (iteracyjnie) ===
            for iteration in range(self.MAX_ITERATIONS):
                state.iterations = iteration + 1
                
                logs.append(AgentLog(
                    step=AgentStep.CRITIQUE,
                    agent_name="Critic",
                    emoji="🧐",
                    message=f"Oceniam jakość (iteracja {iteration + 1})..."
                ))
                
                critique, log, response = self._call_agent(
                    "critic",
                    context,
                    previous_output=current_content
                )
                logs.append(log)
                
                state.critique = critique
                state.critique_score = self._extract_score(critique)
                
                logs.append(AgentLog(
                    step=AgentStep.CRITIQUE,
                    agent_name="Critic",
                    emoji="📊",
                    message=f"Ocena: {state.critique_score}/10"
                ))
                
                # Jeśli wystarczająco dobre - zakończ iteracje
                if state.critique_score >= self.QUALITY_THRESHOLD:
                    logs.append(AgentLog(
                        step=AgentStep.CRITIQUE,
                        agent_name="Critic",
                        emoji="✅",
                        message="Jakość wystarczająca, pomijam dalsze poprawki"
                    ))
                    break
                
                # === KROK 4: EDITOR ===
                logs.append(AgentLog(
                    step=AgentStep.EDITING,
                    agent_name="Editor",
                    emoji="🛠️",
                    message="Wprowadzam poprawki na bazie krytyki..."
                ))
                
                edited, log, response = self._call_agent(
                    "editor",
                    context,
                    previous_output=current_content,
                    critique=critique
                )
                logs.append(log)
                
                if edited:
                    current_content = edited
                    state.edited_content = edited
            
            # === KROK 5: BRAND GUARDIAN ===
            if not skip_brand_check:
                logs.append(AgentLog(
                    step=AgentStep.BRAND_CHECK,
                    agent_name="Brand Guardian",
                    emoji="🛡️",
                    message="Sprawdzam zgodność z Brand DNA..."
                ))
                
                brand_check, log, response = self._call_agent(
                    "brand_guardian",
                    context,
                    previous_output=current_content
                )
                logs.append(log)
                
                state.brand_check_result = brand_check
                state.brand_approved, issues = self._check_brand_compliance(
                    current_content, 
                    brand_check
                )
                
                if state.brand_approved:
                    logs.append(AgentLog(
                        step=AgentStep.BRAND_CHECK,
                        agent_name="Brand Guardian",
                        emoji="✅",
                        message="Treść zgodna z Brand DNA"
                    ))
                else:
                    logs.append(AgentLog(
                        step=AgentStep.BRAND_CHECK,
                        agent_name="Brand Guardian",
                        emoji="⚠️",
                        message=f"Wykryto problemy: {issues[:100]}..."
                    ))
                    
                    # Dodatkowa iteracja edytora dla poprawek brandowych
                    edited, log, response = self._call_agent(
                        "editor",
                        context,
                        previous_output=current_content,
                        critique=f"BRAND ISSUES: {issues}"
                    )
                    if edited:
                        current_content = edited
            else:
                state.brand_approved = True
            
            # === FINALIZACJA ===
            state.final_content = current_content
            state.total_duration_ms = int((time.time() - start_time) * 1000)
            
            logs.append(AgentLog(
                step=AgentStep.FINAL,
                agent_name="Pipeline",
                emoji="🎉",
                message=f"Zakończono w {state.total_duration_ms}ms ({state.iterations} iteracji)"
            ))
            
            # Zapisz do historii
            self.posts_history.add_post(
                content=current_content,
                platform=platform.value,
                topic=topic,
                agent_logs=[log.message for log in logs],
                score=state.critique_score
            )
            
            return AgentResult(
                success=True,
                content=current_content,
                platform=platform.value,
                logs=logs,
                state=state
            )
            
        except Exception as e:
            logger.error(f"Pipeline error: {e}")
            logs.append(AgentLog(
                step=AgentStep.FINAL,
                agent_name="Pipeline",
                emoji="❌",
                message=f"Błąd krytyczny: {str(e)}"
            ))
            
            return AgentResult(
                success=False,
                content="",
                platform=platform.value,
                logs=logs,
                state=state,
                error=str(e)
            )
    
    def run_quick(
        self,
        topic: str,
        platform: Platform,
        style: ContentStyle = ContentStyle.PROFESSIONAL
    ) -> AgentResult:
        """
        Szybki tryb - tylko copywriter bez pełnego pipeline'u.
        Dla prostych przypadków.
        """
        logs: List[AgentLog] = []
        start_time = time.time()
        
        state = PipelineState(
            topic=topic,
            platform=platform,
            goal=ContentGoal.ENGAGEMENT,
            style=style
        )
        
        brand_context = self.brand_memory.get_prompt_context()
        
        context = PromptContext(
            topic=topic,
            platform=platform,
            goal=ContentGoal.ENGAGEMENT,
            style=style,
            brand_context=brand_context
        )
        
        logs.append(AgentLog(
            step=AgentStep.COPYWRITING,
            agent_name="Quick Mode",
            emoji="⚡",
            message="Tryb szybki - bezpośrednie generowanie..."
        ))
        
        content, log, response = self._call_agent("copywriter", context)
        logs.append(log)
        
        state.final_content = content
        state.total_duration_ms = int((time.time() - start_time) * 1000)
        
        return AgentResult(
            success=bool(content),
            content=content,
            platform=platform.value,
            logs=logs,
            state=state,
            error="" if content else "Generation failed"
        )
    
    def regenerate_section(
        self,
        original_content: str,
        section: str,  # "hook", "body", "cta"
        platform: Platform,
        instruction: str = ""
    ) -> Tuple[str, List[AgentLog]]:
        """
        Regeneruje konkretną sekcję posta.
        """
        logs: List[AgentLog] = []
        
        section_prompts = {
            "hook": "Przepisz TYLKO pierwszy akapit (hook). Zrób go bardziej przyciągającym uwagę.",
            "body": "Przepisz środkową część posta. Zachowaj hook i CTA.",
            "cta": "Przepisz TYLKO końcowe Call To Action. Zrób je mocniejsze."
        }
        
        instruction_text = section_prompts.get(section, instruction)
        if instruction:
            instruction_text += f"\n\nDodatkowe wytyczne: {instruction}"
        
        context = PromptContext(
            topic=original_content,
            platform=platform,
            additional_instructions=instruction_text
        )
        
        logs.append(AgentLog(
            step=AgentStep.EDITING,
            agent_name="Section Editor",
            emoji="✂️",
            message=f"Regeneruję sekcję: {section}"
        ))
        
        content, log, _ = self._call_agent(
            "editor",
            context,
            previous_output=original_content
        )
        logs.append(log)
        
        return content, logs
    
    def generate_variations(
        self,
        topic: str,
        platform: Platform,
        count: int = 3,
        styles: List[ContentStyle] = None
    ) -> List[AgentResult]:
        """
        Generuje wiele wariantów tego samego posta.
        """
        if styles is None:
            styles = [
                ContentStyle.PROFESSIONAL,
                ContentStyle.CASUAL,
                ContentStyle.CONTROVERSIAL
            ]
        
        results = []
        
        for i, style in enumerate(styles[:count]):
            result = self.run_quick(topic, platform, style)
            results.append(result)
        
        return results


class CampaignBuilder:
    """
    Buduje kampanie wieloplatformowe.
    Generuje spójną narrację na różne platformy.
    """
    
    def __init__(self, agent_engine: AgentEngine):
        self.engine = agent_engine
    
    def build_campaign(
        self,
        topic: str,
        platforms: List[Platform],
        goal: ContentGoal = ContentGoal.ENGAGEMENT,
        style: ContentStyle = ContentStyle.PROFESSIONAL
    ) -> Dict[str, AgentResult]:
        """
        Generuje kampanię na wiele platform.
        
        Returns:
            Dict z wynikami dla każdej platformy
        """
        results = {}
        
        # Najpierw wygeneruj główną strategię
        primary_platform = platforms[0] if platforms else Platform.LINKEDIN
        
        for platform in platforms:
            logger.info(f"Generating for: {platform.value}")
            result = self.engine.run_pipeline(
                topic=topic,
                platform=platform,
                goal=goal,
                style=style
            )
            results[platform.value] = result
        
        return results
    
    def build_content_series(
        self,
        main_topic: str,
        subtopics: List[str],
        platform: Platform,
        goal: ContentGoal = ContentGoal.AUTHORITY
    ) -> List[AgentResult]:
        """
        Generuje serię powiązanych postów.
        """
        results = []
        
        for i, subtopic in enumerate(subtopics):
            full_topic = f"{main_topic} - Część {i+1}: {subtopic}"
            result = self.engine.run_pipeline(
                topic=full_topic,
                platform=platform,
                goal=goal
            )
            results.append(result)
        
        return results


# === FACTORY FUNCTIONS ===

def create_agent_engine() -> AgentEngine:
    """Factory function dla AgentEngine"""
    return AgentEngine()


def create_campaign_builder() -> CampaignBuilder:
    """Factory function dla CampaignBuilder"""
    engine = create_agent_engine()
    return CampaignBuilder(engine)


# === TESTY MODUŁU ===
if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    
    logging.basicConfig(level=logging.INFO)
    
    print("=== Test Agent Engine ===\n")
    
    engine = AgentEngine()
    
    # Test 1: Quick Mode
    print("1. Quick Mode Test:")
    print("-" * 40)
    
    result = engine.run_quick(
        topic="Dlaczego code review to nie krytyka, tylko inwestycja w zespół",
        platform=Platform.LINKEDIN
    )
    
    print(f"Success: {result.success}")
    print(f"Platform: {result.platform}")
    print(f"\nLogs:")
    for log in result.get_logs_formatted():
        print(f"  {log}")
    
    if result.success:
        print(f"\nContent preview:")
        print(result.content[:300] + "...")
    
    # Test 2: Full Pipeline
    print("\n" + "=" * 50)
    print("2. Full Pipeline Test:")
    print("-" * 40)
    
    result = engine.run_pipeline(
        topic="5 rzeczy których nauczyłem się po 10 latach w IT",
        platform=Platform.LINKEDIN,
        goal=ContentGoal.AUTHORITY,
        style=ContentStyle.PROFESSIONAL
    )
    
    print(f"Success: {result.success}")
    print(f"Iterations: {result.state.iterations}")
    print(f"Critique Score: {result.state.critique_score}/10")
    print(f"Brand Approved: {result.state.brand_approved}")
    print(f"Total Duration: {result.state.total_duration_ms}ms")
    
    print(f"\nFull Logs:")
    for log in result.get_logs_formatted():
        print(f"  {log}")
    
    if result.success:
        print(f"\n{'='*40}")
        print("FINAL CONTENT:")
        print("=" * 40)
        print(result.content)
    
    print("\n✅ Agent Engine działa poprawnie!")
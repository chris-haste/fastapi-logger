"""Enhanced enricher registry with metadata and dependency resolution."""

from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Type

# Move imports to module level for better performance
from ..exceptions import EnricherConfigurationError


@dataclass
class EnricherMetadata:
    """Metadata for registered enrichers."""

    name: str
    enricher_class: Type[Any]
    description: str
    priority: int = 100
    dependencies: List[str] = field(default_factory=list)
    conditions: Dict[str, Any] = field(default_factory=dict)
    async_capable: bool = False


class EnricherRegistry:
    """Enhanced registry for enrichers with metadata support."""

    _enrichers: Dict[str, EnricherMetadata] = {}
    _instances: Dict[str, Any] = {}

    @classmethod
    def register(
        cls,
        name: str,
        enricher_class: Type[Any],
        description: str = "",
        priority: int = 100,
        dependencies: List[str] = None,
        conditions: Dict[str, Any] = None,
        async_capable: bool = False,
    ) -> Type[Any]:
        """Register an enricher with metadata."""
        metadata = EnricherMetadata(
            name=name,
            enricher_class=enricher_class,
            description=description,
            priority=priority,
            dependencies=dependencies or [],
            conditions=conditions or {},
            async_capable=async_capable,
        )
        cls._enrichers[name] = metadata
        return enricher_class

    @classmethod
    def get_metadata(cls, name: str) -> Optional[EnricherMetadata]:
        """Get enricher metadata."""
        return cls._enrichers.get(name)

    @classmethod
    def list_enrichers(cls) -> Dict[str, EnricherMetadata]:
        """List all registered enrichers with metadata."""
        return cls._enrichers.copy()

    @classmethod
    def resolve_dependencies(cls, enricher_names: List[str]) -> List[str]:
        """Resolve enricher dependencies and return sorted order."""
        if not enricher_names:
            return []

        # Build dependency graph
        graph = defaultdict(list)
        in_degree = defaultdict(int)

        # Initialize in_degree for all nodes
        for name in enricher_names:
            in_degree[name] = 0

        # Build graph and calculate in-degrees
        for name in enricher_names:
            metadata = cls._enrichers.get(name)
            if metadata:
                for dependency in metadata.dependencies:
                    if dependency in enricher_names:
                        graph[dependency].append(name)
                        in_degree[name] += 1

        # Topological sort using Kahn's algorithm
        queue = deque([name for name in enricher_names if in_degree[name] == 0])
        result = []

        while queue:
            # Sort by priority to handle nodes with same in-degree consistently
            current_nodes = list(queue)
            queue.clear()

            # Sort by priority (lower number = higher priority)
            current_nodes.sort(
                key=lambda x: cls._enrichers.get(
                    x, EnricherMetadata("", None, "")
                ).priority
            )

            for node in current_nodes:
                result.append(node)

                # Reduce in-degree for neighbors
                for neighbor in graph[node]:
                    in_degree[neighbor] -= 1
                    if in_degree[neighbor] == 0:
                        queue.append(neighbor)

        # Check for cycles
        if len(result) != len(enricher_names):
            remaining = [name for name in enricher_names if name not in result]
            from ..exceptions import EnricherDependencyError

            raise EnricherDependencyError(
                f"Circular dependency detected in enrichers: {remaining}",
                enricher=remaining[0] if remaining else None,
                missing_dependencies=remaining,
            )

        return result

    @classmethod
    def get_instance(cls, name: str, **kwargs) -> Any:
        """Get or create an enricher instance with improved error handling."""
        # Check if instance already exists
        instance_key = f"{name}:{hash(frozenset(kwargs.items()))}"
        if instance_key in cls._instances:
            return cls._instances[instance_key]

        # Get metadata with better error messaging
        metadata = cls._enrichers.get(name)
        if not metadata:
            available_schemes = list(cls._enrichers.keys())
            raise EnricherConfigurationError(
                f"Enricher '{name}' not registered",
                scheme=name,
                available_schemes=available_schemes,
            )

        # Create instance with enhanced error context
        try:
            instance = metadata.enricher_class(**kwargs)

            # Check if this is an async enricher instance
            from .async_enricher import AsyncEnricher

            if isinstance(instance, AsyncEnricher):
                # Validate that metadata correctly indicates async capability
                if not metadata.async_capable:
                    raise EnricherConfigurationError(
                        (f"AsyncEnricher '{name}' not marked as async_capable=True"),
                        scheme=name,
                        error=(
                            "Enricher implements AsyncEnricher but "
                            "metadata.async_capable=False"
                        ),
                    )

                # Wrap async enricher for sync pipeline compatibility
                from .async_pipeline import AsyncEnricherProcessor

                # Create timeout from kwargs or use default
                timeout = kwargs.get("timeout", 5.0)
                wrapped_instance = AsyncEnricherProcessor([instance], timeout=timeout)

                cls._instances[instance_key] = wrapped_instance
                return wrapped_instance

            # For sync enrichers, store instance directly
            # Note: Enrichers don't need to be callable at this level
            # The pipeline will handle the calling interface

            cls._instances[instance_key] = instance
            return instance

        except Exception as e:
            raise EnricherConfigurationError(
                f"Failed to instantiate enricher '{name}': {e}",
                scheme=name,
                params=kwargs,
                error=str(e),
            ) from e

    @classmethod
    def clear_registry(cls) -> None:
        """Clear all registered enrichers (for testing)."""
        cls._enrichers.clear()
        cls._instances.clear()

    @classmethod
    def clear_instances(cls) -> None:
        """Clear all cached instances (for testing)."""
        cls._instances.clear()

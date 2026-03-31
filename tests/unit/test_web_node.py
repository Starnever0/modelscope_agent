import pytest
import json
from unittest.mock import Mock, patch
from langchain_core.documents import Document  
from src.node.web import web_node


class TestWebNode:
    """Test web_node function with TavilySearch."""
    
    def test_web_node_json_string_format(self):
        """Test JSON string format returned by TavilySearch.invoke()."""
        json_result = json.dumps({
            "results": [
                {
                    "content": "First result content",
                    "title": "First Title",
                    "url": "https://example.com/1",
                    "score": 0.95
                },
                {
                    "content": "Second result content",
                    "title": "Second Title", 
                    "url": "https://example.com/2",
                    "score": 0.85
                }
            ]
        })
        
        with patch("src.node.web.TavilySearch") as mock_tavily_class:
            mock_instance = Mock()
            mock_instance.invoke.return_value = json_result
            mock_tavily_class.return_value = mock_instance
            
            state = {"rewritten_query": "test query"}
            result = web_node(state)
            
            assert "retrieved_docs" in result
            docs = result["retrieved_docs"]
            assert len(docs) == 2
            assert docs[0].page_content == "First result content"
            assert docs[0].metadata["title"] == "First Title"
            assert docs[1].metadata["source_type"] == "web"
    
    def test_web_node_dict_format(self):
        """Test dict-based format (backward compatibility)."""
        mock_result = {
            "results": [
                {
                    "content": "First result content",
                    "title": "First Title",
                    "url": "https://example.com/1",
                    "score": 0.95
                }
            ]
        }
        
        with patch("src.node.web.TavilySearch") as mock_tavily_class:
            mock_instance = Mock()
            mock_instance.invoke.return_value = mock_result
            mock_tavily_class.return_value = mock_instance
            
            state = {"rewritten_query": "test query"}
            result = web_node(state)
            
            assert "retrieved_docs" in result
            docs = result["retrieved_docs"]
            assert len(docs) == 1
            assert docs[0].page_content == "First result content"
    
    def test_web_node_list_format(self):
        """Test list-based format (direct results)."""
        mock_results = [
            {
                "content": "First result content",
                "title": "First Title",
                "url": "https://example.com/1",
                "score": 0.95
            }
        ]
        
        with patch("src.node.web.TavilySearch") as mock_tavily_class:
            mock_instance = Mock()
            mock_instance.invoke.return_value = mock_results
            mock_tavily_class.return_value = mock_instance
            
            state = {"rewritten_query": "test query"}
            result = web_node(state)
            
            assert "retrieved_docs" in result
            docs = result["retrieved_docs"]
            assert len(docs) == 1
            assert docs[0].page_content == "First result content"
    
    def test_web_node_empty_results(self):
        """Test with empty search results."""
        json_result = json.dumps({"results": []})
        
        with patch("src.node.web.TavilySearch") as mock_tavily_class:
            mock_instance = Mock()
            mock_instance.invoke.return_value = json_result
            mock_tavily_class.return_value = mock_instance
            
            state = {"rewritten_query": "test query"}
            result = web_node(state)
            
            assert "retrieved_docs" in result
            assert result["retrieved_docs"] == []
    
    def test_web_node_partial_metadata(self):
        """Test with missing optional metadata fields."""
        json_result = json.dumps({
            "results": [
                {
                    "content": "Content only",
                    # title, url, score may be missing
                }
            ]
        })
        
        with patch("src.node.web.TavilySearch") as mock_tavily_class:
            mock_instance = Mock()
            mock_instance.invoke.return_value = json_result
            mock_tavily_class.return_value = mock_instance
            
            state = {"rewritten_query": "test query"}
            result = web_node(state)
            
            docs = result["retrieved_docs"]
            assert len(docs) == 1
            assert docs[0].page_content == "Content only"
            assert docs[0].metadata["title"] == ""
            assert docs[0].metadata["url"] == ""
            assert docs[0].metadata["score"] == 0
    
    def test_web_node_string_fallback(self):
        """Test fallback for plain string result."""
        plain_string = "This is a plain string result"
        
        with patch("src.node.web.TavilySearch") as mock_tavily_class:
            mock_instance = Mock()
            mock_instance.invoke.return_value = plain_string
            mock_tavily_class.return_value = mock_instance
            
            state = {"rewritten_query": "test query"}
            result = web_node(state)
            
            docs = result["retrieved_docs"]
            assert len(docs) == 1
            assert docs[0].page_content == plain_string
            assert docs[0].metadata["title"] == ""
    
    def test_web_node_string_with_dict_items(self):
        """Test edge case where dict inside result list is string."""
        json_result = json.dumps({
            "results": [
                {
                    "content": "Dict result",
                    "title": "Title",
                    "url": "http://example.com",
                    "score": 0.9
                }
            ]
        })
        
        with patch("src.node.web.TavilySearch") as mock_tavily_class:
            mock_instance = Mock()
            mock_instance.invoke.return_value = json_result
            mock_tavily_class.return_value = mock_instance
            
            state = {"rewritten_query": "test query"}
            result = web_node(state)
            
            docs = result["retrieved_docs"]
            assert len(docs) == 1
            assert docs[0].page_content == "Dict result"
            assert docs[0].metadata["title"] == "Title"

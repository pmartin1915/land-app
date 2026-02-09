"""
Input validation middleware for Auction Watcher API

This middleware provides comprehensive input validation and sanitization
for all API endpoints, protecting against injection attacks and malformed data.
"""

import logging
from fastapi import Request, HTTPException
from typing import Any, Dict
import json

from config.validation import (
    InputSanitizer, QueryValidator, ValidationResult,
    validate_property_data, get_validation_summary
)

logger = logging.getLogger(__name__)


class ValidationMiddleware:
    """Comprehensive input validation middleware."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        """Process request through validation middleware."""
        if scope["type"] == "http":
            request = Request(scope, receive)

            # Validate query parameters
            validated_query = await self._validate_query_params(request)
            if not validated_query.get("valid", True):
                # Return validation error
                response = {
                    "detail": "Invalid query parameters",
                    "validation_errors": validated_query.get("errors", [])
                }
                await self._send_error_response(send, 400, response)
                return

            # Validate request body for POST/PUT requests
            if request.method in ["POST", "PUT", "PATCH"]:
                body_validation = await self._validate_request_body(request)
                if not body_validation.get("valid", True):
                    response = {
                        "detail": "Invalid request body",
                        "validation_errors": body_validation.get("errors", [])
                    }
                    await self._send_error_response(send, 400, response)
                    return

        # Continue to next middleware/application
        await self.app(scope, receive, send)

    async def _validate_query_params(self, request: Request) -> Dict[str, Any]:
        """Validate and sanitize query parameters."""
        errors = []
        warnings = []

        for param_name, param_value in request.query_params.items():
            # Skip empty parameters
            if not param_value:
                continue

            try:
                # Validate based on parameter name
                result = self._validate_query_parameter(param_name, param_value)

                if not result.is_valid:
                    errors.extend([f"{param_name}: {error}" for error in result.errors])

                if result.warnings:
                    warnings.extend([f"{param_name}: {warning}" for warning in result.warnings])

                # Log suspicious activity
                if result.errors:
                    logger.warning(f"Query parameter validation failed: {param_name}={param_value}")

            except Exception as e:
                logger.error(f"Error validating query parameter {param_name}: {e}")
                errors.append(f"Validation error for parameter: {param_name}")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }

    def _validate_query_parameter(self, param_name: str, param_value: str) -> ValidationResult:
        """Validate individual query parameter."""

        # Numeric parameters
        numeric_params = {
            "min_price", "max_price", "min_acreage", "max_acreage",
            "min_investment_score", "max_investment_score",
            "min_county_market_score", "min_geographic_score",
            "min_market_timing_score", "page", "page_size"
        }

        if param_name in numeric_params:
            min_val = 0 if param_name.startswith("min_") or param_name in ["page", "page_size"] else None
            max_val = 100 if "score" in param_name else None
            if param_name == "page_size":
                max_val = 1000  # Limit page size to prevent abuse

            return InputSanitizer.sanitize_numeric(
                param_value,
                min_value=min_val,
                max_value=max_val,
                allow_negative=False
            )

        # String parameters
        elif param_name in ["county", "search_query", "year_sold", "sort_by", "sort_order"]:
            max_length = 200 if param_name == "search_query" else 50

            if param_name == "search_query":
                return QueryValidator.validate_search_query(param_value)
            elif param_name in ["sort_by", "sort_order"]:
                return QueryValidator.validate_sort_parameter(param_value)
            else:
                return InputSanitizer.sanitize_string(param_value, max_length=max_length)

        # Boolean parameters
        elif param_name == "water_features":
            if param_value.lower() in ["true", "false", "1", "0"]:
                return ValidationResult(True, param_value.lower() in ["true", "1"], [], [])
            else:
                return ValidationResult(False, False, ["Invalid boolean value"], [])

        # Unknown parameter - still sanitize
        else:
            return InputSanitizer.sanitize_string(param_value, max_length=100)

    async def _validate_request_body(self, request: Request) -> Dict[str, Any]:
        """Validate and sanitize request body data."""
        try:
            # Get request body
            body = await request.body()
            if not body:
                return {"valid": True}

            # Parse JSON
            try:
                data = json.loads(body)
            except json.JSONDecodeError:
                return {
                    "valid": False,
                    "errors": ["Invalid JSON in request body"]
                }

            # Validate property data if it looks like property data
            if isinstance(data, dict) and any(key in data for key in ["parcel_id", "amount", "county"]):
                validation_results = validate_property_data(data)
                summary = get_validation_summary(validation_results)

                if not summary["overall_valid"]:
                    errors = []
                    for field, result in summary["field_results"].items():
                        if result["errors"]:
                            errors.extend([f"{field}: {error}" for error in result["errors"]])

                    return {
                        "valid": False,
                        "errors": errors
                    }

            return {"valid": True}

        except Exception as e:
            logger.error(f"Error validating request body: {e}")
            return {
                "valid": False,
                "errors": ["Request body validation failed"]
            }

    async def _send_error_response(self, send, status_code: int, content: Dict[str, Any]):
        """Send validation error response."""
        response_body = json.dumps(content).encode()

        await send({
            "type": "http.response.start",
            "status": status_code,
            "headers": [
                [b"content-type", b"application/json"],
                [b"content-length", str(len(response_body)).encode()],
            ],
        })

        await send({
            "type": "http.response.body",
            "body": response_body,
        })


def validate_query_params(**validators):
    """
    Decorator for endpoint-specific query parameter validation.

    Usage:
        @validate_query_params(
            county=PropertyValidator.validate_county,
            min_price=lambda x: InputSanitizer.sanitize_numeric(x, min_value=0)
        )
        async def my_endpoint(county: str, min_price: float):
            ...
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Extract request from args/kwargs
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break

            if request is None:
                # Look in kwargs
                request = kwargs.get('request')

            if request:
                # Validate specified parameters
                for param_name, validator in validators.items():
                    param_value = request.query_params.get(param_name)
                    if param_value is not None:
                        try:
                            result = validator(param_value)
                            if hasattr(result, 'is_valid') and not result.is_valid:
                                raise HTTPException(
                                    status_code=400,
                                    detail=f"Invalid {param_name}: {'; '.join(result.errors)}"
                                )
                        except Exception as e:
                            raise HTTPException(
                                status_code=400,
                                detail=f"Validation error for {param_name}: {str(e)}"
                            )

            return await func(*args, **kwargs)
        return wrapper
    return decorator


def sanitize_input(data: Any, field_name: str = "input") -> Any:
    """
    Utility function to sanitize individual input values.

    Args:
        data: Input data to sanitize
        field_name: Name of the field for error reporting

    Returns:
        Sanitized data

    Raises:
        HTTPException: If validation fails
    """
    if isinstance(data, str):
        result = InputSanitizer.sanitize_string(data)
        if not result.is_valid:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid {field_name}: {'; '.join(result.errors)}"
            )
        return result.sanitized_value

    elif isinstance(data, (int, float)):
        result = InputSanitizer.sanitize_numeric(data)
        if not result.is_valid:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid {field_name}: {'; '.join(result.errors)}"
            )
        return result.sanitized_value

    return data
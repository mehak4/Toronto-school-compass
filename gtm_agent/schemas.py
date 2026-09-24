from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid',strict=True,str_strip_whitespace=True)

class Plan(StrictModel):
    approach: str = Field(min_length=1,max_length=1500)
    queries: list[str] = Field(min_length=1,max_length=3)

class Asset(StrictModel):
    channel: Literal['linkedin','email','blog','ads']
    title: str = Field(min_length=1,max_length=250)
    body: str = Field(min_length=1,max_length=12000)
    source_ids: list[int] = Field(min_length=1,max_length=12)

class Campaign(StrictModel):
    assets: list[Asset] = Field(min_length=4,max_length=4)

class ReviewFinding(StrictModel):
    channel: Literal['linkedin','email','blog','ads']
    category: Literal['unsupported_claim','contradiction','missing_requirement','tone']
    draft_quote: str = Field(max_length=1200)
    source_ids: list[int] = Field(max_length=12)
    explanation: str = Field(min_length=1,max_length=1500)

class Critique(StrictModel):
    findings: list[ReviewFinding] = Field(max_length=20)
    summary: str = Field(min_length=1,max_length=2000)


def critique_issues(critique, campaign, evidence):
    """Reject unverifiable reviewer observations; never silently discard them."""
    valid={e['id'] for e in evidence}
    assets={a['channel']:a for a in campaign['assets']}
    errors=[]
    for finding in critique['findings']:
        asset=assets.get(finding['channel'])
        quote=' '.join(finding['draft_quote'].split())
        text=' '.join((asset['title']+' '+asset['body']).split()) if asset else ''
        if finding['category']!='missing_requirement' and not quote:
            errors.append('Quote the actual draft text for claims, contradictions and tone issues.')
        if quote and quote not in text:
            errors.append(f"{finding['channel']}: draft_quote must be copied exactly from that asset.")
        if not set(finding['source_ids']).issubset(valid):
            errors.append('Use only source IDs present in the evidence.')
        if finding['category'] in {'unsupported_claim','contradiction'} and not finding['source_ids']:
            errors.append('Identify the sources checked for each factual issue.')
    return errors


def grounding_issues(campaign, evidence):
    import re
    issues=[]
    if {a['channel'] for a in campaign['assets']} != {'linkedin','email','blog','ads'}:
        issues.append('Provide exactly one asset for each of linkedin, email, blog and ads.')
    valid={e['id'] for e in evidence}
    for a in campaign['assets']:
        refs=set(map(int,re.findall(r'\[(\d+)\]',a['body'])))
        if not refs or not refs.issubset(valid) or set(a['source_ids'])!=refs:
            issues.append(f"{a['channel']}: inline citations must match source_ids and available evidence.")
    return issues

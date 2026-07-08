import { Component } from "../entities/component.entity";
import { ComponentListItemDto } from "../dto/component-list-item.dto";
import { ComponentDetailDto } from "../dto/component-detail.dto";
import { CwlParser } from "../cwl/cwl-parser";

export class ComponentTransformer {
    static toListItem(component: Component): ComponentListItemDto {
        return {
            id: component.id,
            name: component.name,
            repoUrl: component.repoUrl,
            repoCommitSha: component.repoCommitSha ?? null,
            lineageId: component.lineageId,
            version: component.version,
            domain: component.domain,
            source: component.source,
            createdAt: component.createdAt,
        };
    }

    static toDetail(component: Component): ComponentDetailDto {
        return {
            id: component.id,
            name: component.name,
            description: component.description,
            repoUrl: component.repoUrl,
            repoCommitSha: component.repoCommitSha ?? null,
            lineageId: component.lineageId,
            version: component.version,
            cwlContent: CwlParser.injectDescription(component.cwlContent, component.description),
            domain: component.domain,
            source: component.source,
            parameters: component.parameters,
            createdAt: component.createdAt,
        };
    }
}
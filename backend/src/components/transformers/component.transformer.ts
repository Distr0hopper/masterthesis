import { Component } from "../entities/component.entity";
import { Parameter } from "../entities/parameter.entity";
import { ComponentListItemDto } from "../dto/component-list-item.dto";
import { ComponentDetailDto } from "../dto/component-detail.dto";
import { ParameterDto } from "../dto/parameter.dto";
import { CwlParser } from "../cwl/cwl-parser";

export class ComponentTransformer {
    static toListItem(component: Component): ComponentListItemDto {
        return {
            id: component.id,
            name: component.name,
            authorName: component.authorName ?? null,
            repoUrl: component.repoUrl,
            repoCommitSha: component.repoCommitSha ?? null,
            version: component.version,
            domain: component.domain,
            source: component.source,
            createdAt: component.createdAt,
        };
    }

    static toParameter(parameter: Parameter): ParameterDto {
        return {
            id: parameter.id,
            name: parameter.name,
            cwlType: parameter.cwlType,
            defaultValue: parameter.defaultValue ?? null,
            description: parameter.description ?? null,
            direction: parameter.direction,
        };
    }

    static toDetail(component: Component): ComponentDetailDto {
        return {
            id: component.id,
            name: component.name,
            authorName: component.authorName ?? null,
            createdBy: component.createdBy ? { id: component.createdBy.id, email: component.createdBy.email } : null,
            description: component.description,
            repoUrl: component.repoUrl,
            repoCommitSha: component.repoCommitSha ?? null,
            doi: component.doi ?? null,
            version: component.version,
            cwlContent: CwlParser.injectDescription(component.cwlContent, component.description),
            domain: component.domain,
            source: component.source,
            parameters: component.parameters.map(ComponentTransformer.toParameter),
            createdAt: component.createdAt,
        };
    }
}
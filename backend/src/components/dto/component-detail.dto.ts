import { ApiProperty } from "@nestjs/swagger";
import { ComponentDomain, ComponentSource, VALID_DOMAINS } from "../enums";
import { ParameterDto } from "./parameter.dto";

export class ComponentAuthorDto {
    @ApiProperty()
    id: string;

    @ApiProperty()
    email: string;
}

export class ComponentDetailDto {
    @ApiProperty()
    id: string;

    @ApiProperty()
    name: string;

    @ApiProperty({ nullable: true })
    authorName: string | null;

    @ApiProperty({ type: () => ComponentAuthorDto, nullable: true })
    author: ComponentAuthorDto | null;

    @ApiProperty({ nullable: true })
    description: string | null;

    @ApiProperty({ nullable: true })
    repoUrl: string | null;

    @ApiProperty({ nullable: true })
    repoCommitSha: string | null;

    @ApiProperty({ nullable: true })
    doi: string | null;

    @ApiProperty()
    version: number;

    @ApiProperty()
    cwlContent: string;

    @ApiProperty({ enum: VALID_DOMAINS })
    domain: ComponentDomain;

    @ApiProperty({ enum: ComponentSource })
    source: ComponentSource;

    @ApiProperty({ type: () => [ParameterDto] })
    parameters: ParameterDto[];

    @ApiProperty()
    createdAt: Date;
}
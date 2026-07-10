import { ComponentDomain, ComponentSource, VALID_DOMAINS } from "../enums";
import { ApiProperty } from "@nestjs/swagger";
import { IsDate, IsEnum, IsNumber, IsString } from "class-validator";

export class ComponentListItemDto {
    @ApiProperty()
    id: string;

    @ApiProperty({ example: 'RemoveOutliers' })
    @IsString()
    name: string;

    @ApiProperty({ nullable: true })
    author: string | null;

    @ApiProperty({ example: 'https://github.com/movestore/RemoveOutliers', required: false })
    @IsString()
    repoUrl: string;

    @ApiProperty({ nullable: true })
    repoCommitSha: string | null;

    @ApiProperty()
    @IsNumber()
    version: number;

    @ApiProperty({ enum: VALID_DOMAINS, required: false })
    domain: ComponentDomain;

    @ApiProperty({ enum: ComponentSource })
    @IsEnum(ComponentSource)
    source: ComponentSource;

    @ApiProperty()
    @IsDate()
    createdAt: Date;
}